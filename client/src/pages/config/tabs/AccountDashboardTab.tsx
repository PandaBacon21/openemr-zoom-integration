import type { Registration } from "../../../api/config";

interface Props {
  account: Registration;
}

const AccountDashboardTab: React.FC<Props> = ({ account }) => (
  <div>Dashboard tab — {account.zoom_account_id}</div>
);

export default AccountDashboardTab;
