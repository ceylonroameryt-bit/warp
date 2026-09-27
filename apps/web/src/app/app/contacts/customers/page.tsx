import DashboardLayout from "@/components/DashboardLayout";
import ContactListView from "@/components/ContactListView";

export default function CustomersPage() {
  return (
    <DashboardLayout>
      <ContactListView
        initialType="CUSTOMER"
        pageTitle="Customers"
        subtitle="View and manage business clients and accounts ready for future sales invoicing."
      />
    </DashboardLayout>
  );
}
