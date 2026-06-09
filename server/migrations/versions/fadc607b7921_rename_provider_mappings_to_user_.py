"""rename provider_mappings to user_mappings with role flags + remove allow_shared_zoom_user (S11-01 / TD-03)

Sprint 11 cornerstone: unifies the existing ProviderMapping into a UserMapping
table that supports both clinical providers (existing role) and ZCC call-center
agents (new role) via is_provider / is_zcc_agent flags. One row per OpenEMR
user per Zoomly account, regardless of which role(s) they hold.

Also satisfies TD-03 in full:
  - Drops AccountConfig.allow_shared_zoom_user (the previous escape hatch
    that let multiple providers share one Zoom user).
  - Adds GLOBAL partial-unique indices so a Zoom platform user / NPI / ZCC
    user can never be claimed by more than one mapping across the entire
    deployment.
  - Adds a PER-ACCOUNT partial-unique on (zoom_account_id, openemr_user_id)
    so an OpenEMR user can be mapped under multiple Zoom accounts (the
    multi-tenant story) but not twice within the same account.

Schema diff:
  - rename table provider_mappings → user_mappings
  - rename column openemr_provider_id → openemr_user_id (held by any role)
  - relax NOT NULL on openemr_fhir_id, openemr_provider_npi (provider-only fields)
  - add columns: is_provider, is_zcc_agent, zcc_user_id, agent_role
  - drop account_configs.allow_shared_zoom_user

Revision ID: fadc607b7921
Revises: c1d2e3f4a5b6
Create Date: 2026-06-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fadc607b7921"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Rename the table
    op.rename_table("provider_mappings", "user_mappings")

    # 2. Rename openemr_provider_id → openemr_user_id wherever it lives.
    #    Semantic clarification: the column always meant "the OpenEMR users.id" —
    #    in audit_log it's the user that performed/received the action; in
    #    meeting_records it's the provider hosting the meeting; in user_mappings
    #    it's the OpenEMR user the row maps (now any role, not just providers).
    #    Renaming all three keeps the column name consistent across the schema.
    with op.batch_alter_table("user_mappings") as batch_op:
        batch_op.alter_column(
            "openemr_provider_id",
            new_column_name="openemr_user_id",
            existing_type=sa.String(length=128),
            existing_nullable=True,
        )
    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.alter_column(
            "openemr_provider_id",
            new_column_name="openemr_user_id",
            existing_type=sa.String(length=128),
            existing_nullable=True,
        )
    with op.batch_alter_table("meeting_records") as batch_op:
        batch_op.alter_column(
            "openemr_provider_id",
            new_column_name="openemr_user_id",
            existing_type=sa.String(length=128),
            existing_nullable=False,
        )

    # 3. Relax NOT NULL on provider-only fields. Pure ZCC agents won't have these.
    with op.batch_alter_table("user_mappings") as batch_op:
        batch_op.alter_column(
            "openemr_fhir_id", existing_type=sa.String(length=128), nullable=True
        )
        batch_op.alter_column(
            "openemr_provider_npi", existing_type=sa.String(length=10), nullable=True
        )

    # 4. Add role flags + ZCC-agent fields.
    #    server_default on is_provider=true backfills existing rows (they were all
    #    providers). New rows from the ORM get default=False at the application
    #    level — service layer must set the intended role explicitly.
    with op.batch_alter_table("user_mappings") as batch_op:
        batch_op.add_column(
            sa.Column("is_provider", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.add_column(
            sa.Column("is_zcc_agent", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("zcc_user_id", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("agent_role", sa.String(length=64), nullable=True))

    # 5. Partial-unique indices.
    #    Postgres-specific via postgresql_where. The deployment runs on Postgres
    #    (zoom-bridge's app DB) so this is safe; if we ever move to SQLite for
    #    tests, the indices are no-ops there which is acceptable for unit-test scope.

    # Global: a Zoom platform user can be a provider for at most one active mapping
    # anywhere across the deployment (closes TD-03 for provider role).
    op.create_index(
        "ix_user_mappings_zoom_user_id_unique_active_provider",
        "user_mappings",
        ["zoom_user_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_active = true AND is_provider = true AND zoom_user_id IS NOT NULL"
        ),
    )

    # Global: an NPI can be claimed by at most one active provider mapping
    # anywhere (closes TD-03 for NPI).
    op.create_index(
        "ix_user_mappings_openemr_provider_npi_unique_active_provider",
        "user_mappings",
        ["openemr_provider_npi"],
        unique=True,
        postgresql_where=sa.text(
            "is_active = true AND is_provider = true AND openemr_provider_npi IS NOT NULL"
        ),
    )

    # Global: a ZCC user ID can be claimed by at most one active agent mapping
    # anywhere (matches Josh's "no shared users across accounts" rule).
    op.create_index(
        "ix_user_mappings_zcc_user_id_unique_active_agent",
        "user_mappings",
        ["zcc_user_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_active = true AND is_zcc_agent = true AND zcc_user_id IS NOT NULL"
        ),
    )

    # Per-account: an OpenEMR user appears in at most one active mapping row per
    # Zoomly account, regardless of which role(s) the row holds. (Allows the
    # same OpenEMR install to be mapped under multiple Zoomly accounts — the
    # multi-tenant story — but never twice within the same account.)
    op.create_index(
        "ix_user_mappings_openemr_user_id_unique_per_account",
        "user_mappings",
        ["zoom_account_id", "openemr_user_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_active = true AND openemr_user_id IS NOT NULL"
        ),
    )

    # 6. Drop AccountConfig.allow_shared_zoom_user — TD-03 cleanup.
    with op.batch_alter_table("account_configs") as batch_op:
        batch_op.drop_column("allow_shared_zoom_user")


def downgrade() -> None:
    """Downgrade schema."""
    # 6. Restore allow_shared_zoom_user
    with op.batch_alter_table("account_configs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "allow_shared_zoom_user",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

    # 5. Drop the partial-unique indices
    op.drop_index(
        "ix_user_mappings_openemr_user_id_unique_per_account", table_name="user_mappings"
    )
    op.drop_index(
        "ix_user_mappings_zcc_user_id_unique_active_agent", table_name="user_mappings"
    )
    op.drop_index(
        "ix_user_mappings_openemr_provider_npi_unique_active_provider",
        table_name="user_mappings",
    )
    op.drop_index(
        "ix_user_mappings_zoom_user_id_unique_active_provider",
        table_name="user_mappings",
    )

    # 4. Drop role + ZCC-agent columns
    with op.batch_alter_table("user_mappings") as batch_op:
        batch_op.drop_column("agent_role")
        batch_op.drop_column("zcc_user_id")
        batch_op.drop_column("is_zcc_agent")
        batch_op.drop_column("is_provider")

    # 3. Restore NOT NULL constraints
    with op.batch_alter_table("user_mappings") as batch_op:
        batch_op.alter_column(
            "openemr_provider_npi", existing_type=sa.String(length=10), nullable=False
        )
        batch_op.alter_column(
            "openemr_fhir_id", existing_type=sa.String(length=128), nullable=False
        )

    # 2. Rename openemr_user_id back to openemr_provider_id on all three tables
    with op.batch_alter_table("meeting_records") as batch_op:
        batch_op.alter_column(
            "openemr_user_id",
            new_column_name="openemr_provider_id",
            existing_type=sa.String(length=128),
            existing_nullable=False,
        )
    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.alter_column(
            "openemr_user_id",
            new_column_name="openemr_provider_id",
            existing_type=sa.String(length=128),
            existing_nullable=True,
        )
    with op.batch_alter_table("user_mappings") as batch_op:
        batch_op.alter_column(
            "openemr_user_id",
            new_column_name="openemr_provider_id",
            existing_type=sa.String(length=128),
            existing_nullable=True,
        )

    # 1. Rename table back
    op.rename_table("user_mappings", "provider_mappings")
