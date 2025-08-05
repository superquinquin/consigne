import { API_ADDRESS, type ApiResponse } from '@/services/api.utils.ts'

/*
 exemple:
 [
   [
     1615,
     "1615 - BAGLIN, Marine"
   ],
   [
     2615,
     "2615 - Enercoop HDF"
   ],
   [
     615,
     "615 - CAVAREC, Romain"
   ],
   [
     615,
     "615 - PEINGNEZ, Sabine, SZEREMETA, Rémi"
   ]
 ]
*/

export type SearchUserResponse = {
  matches: [number, string][]
}

export type GetShiftsUsersResponse = {
  users: [number, string][]
}

export type User = {
  coopNumber: number
  firstName?: string
  lastName?: string
  fullName: string
  profilePictureUrl?: string
}

export default {
  searchUser: async (input: string): Promise<ApiResponse<SearchUserResponse>> => {
    console.log(`${API_ADDRESS}/search-user`);
    const response = await fetch(`${API_ADDRESS}/search-user`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json;charset=UTF-8',
      },
      body: JSON.stringify({ input }),
    })
    return response.json()
  },

  getShiftsUsers: async (): Promise<ApiResponse<GetShiftsUsersResponse>> => {
    console.log(`${API_ADDRESS}/get-shifts-users`)
    const response = await fetch(`${API_ADDRESS}/get-shifts-users`, {
      method: 'GET',
      headers: {
        'content-type': 'application/json;charset=UTF-8',
      },
    })

    return response.json()
  },

  parseUser: (apiUser: [number, string]): User => {
    const [coopNumber, nameWithCoopNumber] = apiUser

    const deduceFirstAndLastName = (
      name: string,
    ): { fullName: string; firstName?: string; lastName?: string } => {
      const [_, nameWithoutCoopNumber] = name.split(' - ')
      const splittedName = nameWithoutCoopNumber.trim().split(',')

      if (splittedName.length === 2) {
        return {
          fullName: nameWithoutCoopNumber,
          firstName: splittedName[1],
          lastName: splittedName[0],
        }
      }

      return { fullName: nameWithoutCoopNumber }
    }

    return {
      coopNumber,
      ...deduceFirstAndLastName(nameWithCoopNumber),
    }
  },
}
