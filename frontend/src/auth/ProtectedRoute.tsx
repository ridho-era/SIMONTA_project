import type { ReactElement } from "react";
import { Navigate } from "react-router-dom";

import { FullPageLoader } from "../components/Loader";
import { homePath } from "../config/navigation";
import type { Role } from "../lib/types";
import { useAuth } from "./AuthContext";

export function ProtectedRoute({ roles, children }: { roles: Role[]; children: ReactElement }) {
  const { user, isLoading } = useAuth();

  if (isLoading) return <FullPageLoader />;
  if (!user) return <Navigate to="/masuk" replace />;
  if (user.must_change_password) return <Navigate to="/ganti-password" replace />;
  if (!roles.includes(user.role)) return <Navigate to={homePath(user.role)} replace />;
  return children;
}

export function RootRedirect() {
  const { user, isLoading } = useAuth();

  if (isLoading) return <FullPageLoader />;
  if (!user) return <Navigate to="/masuk" replace />;
  return <Navigate to={user.must_change_password ? "/ganti-password" : homePath(user.role)} replace />;
}