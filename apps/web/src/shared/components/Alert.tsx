export function Alert({
  children,
  tone = "error",
}: {
  children: string;
  tone?: "error" | "success";
}) {
  return (
    <div
      className={tone === "error" ? "error-card" : "success-card"}
      role={tone === "error" ? "alert" : "status"}
    >
      {children}
    </div>
  );
}
