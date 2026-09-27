import DashboardLayout from "@/components/DashboardLayout";
import ContactListView from "@/components/ContactListView";

export default function SuppliersPage() {
  return (
    <DashboardLayout>
      <ContactListView
        initialType="SUPPLIER"
        pageTitle="Suppliers"
        subtitle="Manage vendors, service providers, and accounts payable contacts."
      />
    </DashboardLayout>
  );
}
