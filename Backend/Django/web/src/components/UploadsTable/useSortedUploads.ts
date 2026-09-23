import { useMemo } from 'react';
import { File, SortConfig } from './types';

export const useSortedUploads = (uploads: File[], sortConfig: SortConfig) => {
    return useMemo(() => {
        let sortableUploads = [...uploads];
        if (sortConfig.key !== null) {
            sortableUploads.sort((a, b) => {
                if (a[sortConfig.key!] < b[sortConfig.key!]) {
                    return sortConfig.direction === 'ascending' ? -1 : 1;
                }
                if (a[sortConfig.key!] > b[sortConfig.key!]) {
                    return sortConfig.direction === 'ascending' ? 1 : -1;
                }
                return 0;
            });
        }
        return sortableUploads;
    }, [uploads, sortConfig]);
};
