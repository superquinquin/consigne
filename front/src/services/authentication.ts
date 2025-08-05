import {type ApiResponse, API_ADDRESS} from "@/services/api.utils.ts";

export type AuthenticateResponse = {
  auth: boolean,
  user?: {
    user_name: string,
    user_code: string
  };
}

export type SearchUserResponse = {
  matches: any
}

export default  {
   authenticate: async (username: string, password: string): Promise<ApiResponse<AuthenticateResponse>> => {
    const response = await fetch(`${API_ADDRESS}/auth_provider`,
      {
        method: 'POST',
        headers: {
          'content-type': 'application/json;charset=UTF-8',
        },
        body: JSON.stringify({username, password})
      });

    return response.json();
  },

  searchUser: async (input: string): Promise<ApiResponse<SearchUserResponse>> => {
    const response = await fetch(`${API_ADDRESS}/search-user`,
      {
        method: 'POST',
        headers: {
          'content-type': 'application/json;charset=UTF-8',
        },
        body: JSON.stringify({input})
      });

    return response.json();
  }
}
