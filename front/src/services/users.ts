import type { ApiResponse } from '@/services/api.utils.ts'

export type SearchUserResponse = {
  matches: any
}

export type GetShiftsUsersResponse = {
  users: any
}

export default {
  searchUser: async (input: string): Promise<ApiResponse<SearchUserResponse>> => {
    const response = await fetch('http://localhost:8000/search-user', {
      method: 'POST',
      headers: {
        'content-type': 'application/json;charset=UTF-8',
      },
      body: JSON.stringify({ input }),
    })

    return response.json()
  },

  getShiftsUsers: async (): Promise<ApiResponse<GetShiftsUsersResponse>> => {
    const response = await fetch('http://localhost:8000/get-shifts-users', {
      method: 'GET',
      headers: {
        'content-type': 'application/json;charset=UTF-8',
      },
    })

    return response.json()
  },
}
