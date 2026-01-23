import { API_ADDRESS, type ApiResponse } from '@/services/api.utils.ts'

export type CreateResponse = {
  deposit_id: number
}

export type GetByIdResponse = {
  deposit: Record<any, any>
  receiver: Record<any, any>
  provider: Record<any, any>
  deposit_lines: Record<any, any>[]
}

export type GetByIdAndLineIdResponse = {
  deposit_lines: Record<any, any>
}

export type AddProductResponse = {
  deposit_line_id: number
  name: string
  odoo_product_id: number
  product_id: number
  returnable: boolean
  return_value?: number
}
export default {
  create: async function (providerCode: number, receiverCode: number): Promise<CreateResponse> {
    // For the API, persons receiving returnables are considered as providers
    // And persons receiving the tickets are considered as receivers
    const response = await fetch(`${API_ADDRESS}/deposit/create`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json;charset=UTF-8',
      },
      body: JSON.stringify({ receiver_partner_id: providerCode, provider_partner_id: receiverCode }),
    })

    return response.json().then(({ data }: ApiResponse<CreateResponse>) => data)
  },

  getById: async function (depositId: string): Promise<GetByIdResponse> {
    const response = await fetch(`${API_ADDRESS}/deposit/${depositId}`, {
      method: 'GET',
      headers: { 'content-type': 'application/json;charset=UTF-8' },
    })

    return response.json().then(({ data }: ApiResponse<GetByIdResponse>) => data)
  },

  getByIdAndLineId: async function (
    depositId: string,
    lineId: string,
  ): Promise<GetByIdAndLineIdResponse> {
    const response = await fetch(`${API_ADDRESS}/deposit/${depositId}/${lineId}`, {
      method: 'GET',
      headers: { 'content-type': 'application/json;charset=UTF-8' },
    })

    return response.json().then(({ data }: ApiResponse<GetByIdAndLineIdResponse>) => data)
  },

  addProduct: async function (
    depositId: number,
    productCode: string,
  ): Promise<ApiResponse<AddProductResponse | void>> {
    const response = await fetch(
      `${API_ADDRESS}/deposit/${depositId}/return/${productCode}`,
      {
        method: 'GET',
        headers: { 'content-type': 'application/json;charset=UTF-8' },
      },
    )

    return response.json() as Promise<ApiResponse<AddProductResponse | void>>
  },

  cancelProduct: async function (depositId: number, lineId: string): Promise<void> {
    const response = await fetch(`${API_ADDRESS}/deposit/${depositId}/cancel/${lineId}`, {
      method: 'GET',
      headers: { 'content-type': 'application/json;charset=UTF-8' },
    })

    return response.json().then(({ data }: ApiResponse<void>) => data)
  },

  printTicket: async function (depositId: number): Promise<void> {
    const response = await fetch(`${API_ADDRESS}/deposit/${depositId}/ticket`, {
      method: 'GET',
      headers: { 'content-type': 'application/json;charset=UTF-8' },
    })

    return response.json().then(({ data }: ApiResponse<void>) => data)
  },

  close: async function (depositId: number): Promise<ApiResponse<void>> {
    const response = await fetch(`${API_ADDRESS}/deposit/${depositId}/close`, {
      method: 'GET',
      headers: { 'content-type': 'application/json;charset=UTF-8' },
    })

    return response.json()
  },
}
