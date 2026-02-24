import dynamic from "next/dynamic";

const VulnSentinelDashboard = dynamic(
  () => import("@/components/VulnSentinelDashboard"),
  { ssr: false }
);

export default function Page() {
  return <VulnSentinelDashboard />;
}
