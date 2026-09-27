"use client";

import React, { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Verification token is missing.");
      return;
    }

    const verify = async () => {
      try {
        const res = await fetch("/api/v1/auth/verify-email", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || data.message || "Invalid or expired token.");
        }

        setStatus("success");
      } catch (err: any) {
        setStatus("error");
        setMessage(err.message || "Verification failed.");
      }
    };

    verify();
  }, [token]);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-sm border border-slate-200 rounded-2xl sm:px-10 text-center">
          {status === "loading" && (
            <div className="py-6">
              <Loader2 className="w-10 h-10 text-blue-600 animate-spin mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900">Verifying your email...</h3>
              <p className="text-sm text-slate-500 mt-1">Please wait while we confirm your credentials.</p>
            </div>
          )}

          {status === "success" && (
            <div className="py-4">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-emerald-100 mb-4">
                <CheckCircle2 className="h-6 w-6 text-emerald-600" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900">Email Verified!</h3>
              <p className="text-sm text-slate-600 mt-2">
                Your email has been confirmed. You can now log into your accounting workspace.
              </p>
              <div className="mt-6">
                <Link
                  href="/login"
                  className="w-full inline-flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
                >
                  Sign In to Dashboard
                </Link>
              </div>
            </div>
          )}

          {status === "error" && (
            <div className="py-4">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
                <XCircle className="h-6 w-6 text-red-600" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900">Verification Link Expired</h3>
              <p className="text-sm text-slate-600 mt-2">
                {message || "The verification link is invalid or has already expired."}
              </p>
              <div className="mt-6">
                <Link
                  href="/login"
                  className="w-full inline-flex justify-center py-2.5 px-4 border border-slate-300 rounded-lg shadow-sm text-sm font-medium text-slate-700 bg-white hover:bg-slate-50"
                >
                  Return to Sign In
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-50 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
        </div>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}
