import { AppSidebar } from "@/components/nav/AppSidebar";
import { StudentProvider } from "@/lib/useStudent";

export default function RoutesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <StudentProvider>
      <AppSidebar>{children}</AppSidebar>
    </StudentProvider>
  );
}
