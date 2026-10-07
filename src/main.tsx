import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "./routes";
import { WalletProvider } from "@/components/wallet-provider";
import { TransactionProvider } from "@/components/transaction-provider";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <WalletProvider>
      <TransactionProvider>
        <RouterProvider router={router} />
      </TransactionProvider>
    </WalletProvider>
  </StrictMode>,
);
