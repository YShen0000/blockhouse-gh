export interface File {
    id: number;
    user_id: number;
    file_name: string;
    upload_date: string;
    file_size: number;
}

export interface SortConfig {
    key: keyof File | null;
    direction: 'ascending' | 'descending';
}