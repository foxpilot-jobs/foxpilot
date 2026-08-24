import { ScanSearch, Sparkles } from "lucide-react";
import { Button } from "../../../shared/ui/Button";

export function ProfileActions({
  disabled,
  onMatching,
  onScan,
}: {
  disabled: boolean;
  onMatching: () => void;
  onScan: () => void;
}) {
  return (
    <section className="profile-actions">
      <div className="profile-section-heading">
        <p className="ui-eyebrow">Keep your workspace fresh</p>
        <h2>Profile actions</h2>
      </div>
      <div className="profile-action-buttons">
        <Button
          disabled={disabled}
          icon={<ScanSearch size={18} />}
          variant="outline"
          onClick={onScan}
        >
          Run job scan
        </Button>
        <Button disabled={disabled} icon={<Sparkles size={18} />} onClick={onMatching}>
          Run matching
        </Button>
      </div>
    </section>
  );
}
