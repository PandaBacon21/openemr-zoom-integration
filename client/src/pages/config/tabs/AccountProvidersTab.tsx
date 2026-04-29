import type { Registration } from "../../../api/config";

interface Props {
  account: Registration;
}

const AccountProvidersTab: React.FC<Props> = ({ account }) => (
  <div>Providers tab — {account.zoom_account_id}</div>
);

export default AccountProvidersTab;
