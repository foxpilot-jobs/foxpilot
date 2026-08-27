import { Sparkles } from "lucide-react";
import { Button } from "../../../shared/ui/Button";

export function ProfileActions({
  disabled,
  loading,
  onMatching,
}: {
  disabled: boolean;
  loading: boolean;
  onMatching: () => void;
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
          icon={<Sparkles size={18} />}
          loading={loading}
          onClick={onMatching}
        >
          Run matching
        </Button>
      </div>
    </section>
  );
}
