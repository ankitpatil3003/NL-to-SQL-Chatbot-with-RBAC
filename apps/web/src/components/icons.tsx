// A handful of inline stroke icons (no icon library dependency).
import type { SVGProps } from "react";

function Icon({ children, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      {...props}
    >
      {children}
    </svg>
  );
}

export const PlusIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}><path d="M12 5v14M5 12h14" /></Icon>
);
export const SidebarIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M9 4v16" /></Icon>
);
export const SendIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}><path d="M12 19V5M5 12l7-7 7 7" /></Icon>
);
export const StopIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}><rect x="6" y="6" width="12" height="12" rx="2" /></Icon>
);
export const TrashIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" /></Icon>
);
export const PencilIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}><path d="M4 20h4L19 9l-4-4L4 16v4z" /></Icon>
);
export const CopyIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V5a2 2 0 0 1 2-2h10" /></Icon>
);
export const CheckIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}><path d="M5 12l5 5L20 7" /></Icon>
);
export const SunIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></Icon>
);
export const MoonIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" /></Icon>
);
export const MonitorIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M8 20h8M12 16v4" /></Icon>
);
export const LogoutIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 17l5-5-5-5M15 12H4" /></Icon>
);
export const DownloadIcon = (p: SVGProps<SVGSVGElement>) => (
  <Icon {...p}><path d="M12 4v11M7 10l5 5 5-5M5 20h14" /></Icon>
);
