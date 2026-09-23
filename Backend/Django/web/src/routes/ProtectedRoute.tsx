import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useEffect, useState } from "react";

interface IProtectedRoute {
    children?: React.ReactNode;
}

export const ProtectedRoute: React.FC<IProtectedRoute> = ({children}) => {
  const [isLoggedIn] = useAuth();

    if (isLoggedIn) {
      return <>{children}</>
    }

    return <Navigate to="/" />;  
};
