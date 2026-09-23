import { useState, useEffect, useLayoutEffect } from 'react';

const useContainerDimensions = (containerRef: React.RefObject<HTMLElement>): { width: number, height: number } => {
    const [containerDimensions, setContainerDimensions] = useState({
        width: 0,
        height: 0,
    });

    const handleResize = () => {
        if (containerRef.current) {
            const { width, height } = containerRef.current.getBoundingClientRect();
            setContainerDimensions({ width, height });
        }
    };

    useLayoutEffect(() => {
        handleResize(); // Initial call to handleResize

        const resizeObserver = new ResizeObserver(() => {
            requestAnimationFrame(handleResize);
        });

        if (containerRef.current) {
            resizeObserver.observe(containerRef.current);
        }

        return () => {
            if (containerRef.current) {
                resizeObserver.unobserve(containerRef.current);
            }
        };
    }, []);
    useLayoutEffect(() => {
        const observer = new MutationObserver(() => {
            handleResize();
        });

        if (containerRef.current) {
            observer.observe(containerRef.current, {
                attributes: true,
                childList: true,
                characterData: true,
            });
        }

        return () => observer.disconnect();
    }, []);
    return containerDimensions;
};

export default useContainerDimensions;
