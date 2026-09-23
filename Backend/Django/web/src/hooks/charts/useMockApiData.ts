import { useState, useEffect } from 'react';




const useMockApiData = (mock: any) => {
    const [data, setData] = useState();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        // Simulate a fetch call with a delay
        const fetchData = async () => {
            try {
                setLoading(true);
                // Mock JSON data
                const mockData = mock
                // Simulate fetch delay
                await new Promise(resolve => setTimeout(resolve, Math.floor(Math.random() * 2001)));
                setData(mockData);
            } catch (error) {
                setError(error as Error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [mock]); // Empty dependency array means this effect runs once on mount

    return [data, loading, error];
};

export default useMockApiData;
