import { useState, useEffect } from 'react';
import axios from 'axios';


const useApi = (route: string, method: string = 'GET', body?: any) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const token = localStorage.getItem("token");

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await axios(route, {
                    method,
                    data: body,
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                });
                setData(response.data);
            } catch (e) {
                if (axios.isAxiosError(e)) {
                    setError(e.response?.statusText || e.message);
                } else if (e instanceof Error) {
                    setError(e.message);
                } else {
                    setError('An unexpected error occurred');
                }
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [route, method, body]);

    return { data, loading, error };
};

export default useApi;
