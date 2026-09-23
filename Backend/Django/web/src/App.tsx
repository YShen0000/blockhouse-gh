import React, { useEffect } from "react";
import { BrowserRouter as Router } from "react-router-dom";
import { Routes } from "./routes";
import { initializeAmplitude, logEvent } from "./utils/analytics";

import NavBar from "./components/Navbar/Navbar";

import "./App.css";

const App: React.FC = () => {
    useEffect(() => {
        initializeAmplitude();
    }, []);

    return (
        <Router>
            <div className="App">
                <NavBar />
                {/* Header component here, if any */}
                <Routes />
                {/* Footer component here, if any */}
            </div>
        </Router>
    );
};

export default App;
