"use client";

interface CollapsibleDrawerProps {
  open: boolean;
  width: string;
  children: React.ReactNode;
}

export function CollapsibleDrawer({
  open,
  width,
  children,
}: CollapsibleDrawerProps) {
  return (
    <aside
      className={`absolute left-0 top-0 bottom-0 ${width} z-10 border-r border-stone-200/60 bg-white transition-transform duration-300 ease-in-out ${
        open ? "translate-x-0" : "-translate-x-full"
      }`}
    >
      {children}
    </aside>
  );
}
