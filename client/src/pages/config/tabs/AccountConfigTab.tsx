import type { Registration } from "../../../api/config";

interface Props {
  account: Registration;
  isVerified: boolean;
  onAccountUpdated: (account: Registration) => void;
}

const AccountConfigTab: React.FC<Props> = ({ account }) => (
  <div>Config tab — {account.zoom_account_id}</div>
);

export default AccountConfigTab;
