import React from "react";
import { Routes, Route } from "react-router-dom";
import { ProtectedRoute } from "./ProtectedRoute";
import ExternalRedirect from "./ExternalRedirect";

import Home from "../pages/Home/Home";
import Upload from "../pages/Upload/Upload";
import UploadsList from "../pages/UploadsList/UploadsList";
import Analytics from "../pages/Analytics/Analytics";
import SelectFiles from "../pages/SelectFiles/SelectFiles";
import PrivacyPolicy from "../pages/PrivacyPolicy/PrivacyPolicy";
import TermsOfService from "../pages/TermsOfService/TermsOfService";

const careersLink =
    "https://blockhouse1.notion.site/Job-Board-1dfb7c9117434ab0ac7acf634dd723cb?pvs=4";

const AppRoutes: React.FC = () => (
    <Routes>
        <Route path="/" element={<Home />} />
        <Route
            path="/upload"
            element={
                <ProtectedRoute>
                    <Upload />
                </ProtectedRoute>
            }
        />
        <Route
            path="/select-files"
            element={
                <ProtectedRoute>
                    <SelectFiles />
                </ProtectedRoute>
            }
        />
        <Route
            path="/list"
            element={
                <ProtectedRoute>
                    <UploadsList />
                </ProtectedRoute>
            }
        />
        <Route
            path="/analytics/:key"
            element={
                <ProtectedRoute>
                    <Analytics />
                </ProtectedRoute>
            }
        />
        <Route
            path="/demo"
            element={
                <Analytics />
            }
        />
        <Route path="/privacy-policy" element={<PrivacyPolicy />} />
        <Route path="/terms-of-service" element={<TermsOfService />} />

        <Route
            path="/careers"
            element={<ExternalRedirect to={careersLink} />}
        />
    </Routes>
);

export default AppRoutes;
