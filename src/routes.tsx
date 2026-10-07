import { createBrowserRouter } from "react-router-dom";
import Layout from "@/components/layout";
import Home from "@/pages/home";
import Policies from "@/pages/policies";
import PolicyPage from "@/pages/policy";
import { getPolicy, getSummary, listPolicies } from "@/lib/genlayer";

// Page data is fetched by route loaders (plain reads, no wallet needed).
export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Home />, loader: () => getSummary().catch(() => ({ pool_balance: 0n, outstanding_liability: 0n, quote_count: 0, policy_count: 0 })) },
      { path: "policies", element: <Policies />, loader: () => listPolicies().catch(() => []) },
      { path: "policy/:policyId", element: <PolicyPage />, loader: ({ params }) => getPolicy(params.policyId ?? "").catch(() => null) },
    ],
  },
]);
