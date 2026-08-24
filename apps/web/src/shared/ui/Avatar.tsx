export function Avatar({
  image,
  initials,
  alt = "",
}: {
  image?: string;
  initials?: string;
  alt?: string;
}) {
  return image ? (
    <img alt={alt} className="ui-avatar" src={image} />
  ) : (
    <span className="ui-avatar ui-avatar-fallback">{initials ?? "?"}</span>
  );
}
