export const API_ADDRESS: string = "https://consigne.superquinquin.fr/api"; // http://localhost:8124

export type ApiResponse<T> = {
  status: number
  reasons: string
  data: T
}

export type ApiError = ApiResponse<void> & { __typename: 'ApiError' }
