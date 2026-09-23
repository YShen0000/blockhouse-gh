import { useEffect, useState } from "react";

export const useAuth = (): [isLoggedIn: boolean] => {
    const [isLoggedIn, setLoggedIn] = useState<boolean>(localStorage.getItem('token') ? true : false);

    useEffect(() => {
        setLoggedIn(localStorage.getItem('token') ? true : false)
    }, [localStorage.getItem('token')])

    return [isLoggedIn];
};