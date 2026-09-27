import DashboardLayout from "@/components/DashboardLayout";
import ContactListView from "@/components/ContactListView";

export default function ContactsPage() {
  return (
    <DashboardLayout>
      <ContactListView
        initialType="ALL"
        pageTitle="Business Contacts"
        subtitle="Manage all customers, suppliers, and two-way business relationships in one unified directory."
      />
    </DashboardLayout>
  );
}
