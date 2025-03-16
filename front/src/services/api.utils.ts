export type ApiResponse<T> = {
  status: number;
  reasons: string;
  data: T;
}
