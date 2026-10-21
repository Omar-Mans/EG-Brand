/** EG Brand mark: three right-aligned lines of content (Arabic reads right to left) and a spark, the AI. */
export function LogoMark({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <rect width="64" height="64" rx="16" fill="#E9A23B" />
      <rect x="18" y="17" width="30" height="7" rx="3.5" fill="#14152A" />
      <rect x="26" y="29" width="22" height="7" rx="3.5" fill="#14152A" />
      <rect x="22" y="41" width="26" height="7" rx="3.5" fill="#14152A" />
      <path d="M15 34.5l2.2-4.8 4.8-2.2-4.8-2.2L15 20.5l-2.2 4.8-4.8 2.2 4.8 2.2z" fill="#FFFFFF" />
    </svg>
  );
}

export default function Logo({ size = 32, href }: { size?: number; href?: string }) {
  const inner = <><LogoMark size={size} /><span>EG <b>Brand</b></span></>;
  return href ? <a href={href} className="mark" aria-label="EG Brand">{inner}</a> : <span className="mark">{inner}</span>;
}
