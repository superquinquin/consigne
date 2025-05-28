export type ApiResponse<T> = {
  status: number
  reasons: string
  data: T
}

export type ApiError = ApiResponse<void> & { __typename: 'ApiError' }
