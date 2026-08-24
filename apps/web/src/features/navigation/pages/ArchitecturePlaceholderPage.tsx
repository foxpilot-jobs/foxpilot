import { PageContainer, PageHeader } from "../../../shared/ui/AppShell";

export function ArchitecturePlaceholderPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <PageContainer>
      <PageHeader description={description} title={title} />
      <div className="ui-architecture-placeholder">
        This workspace is reserved for the next FoxPilot product phase.
      </div>
    </PageContainer>
  );
}
