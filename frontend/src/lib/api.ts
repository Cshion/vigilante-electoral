// API client for electoral backend

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// SWR fetcher function
export const fetcher = async <T>(url: string): Promise<T> => {
  const response = await fetch(`${API_URL}${url}`);
  if (!response.ok) {
    throw new Error('Failed to fetch');
  }
  return response.json();
};
