import { AppSidebar } from "@/components/nav/AppSidebar";

export default function RoutesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppSidebar>{children}</AppSidebar>;
}
