import type { ApiResponse } from '@/services/api.utils.ts'

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
  create: async function (providerCode: string, receiverCode: string): Promise<CreateResponse> {
    const response = await fetch('http://localhost:8000/deposit/create', {
      method: 'POST',
      headers: {
        'content-type': 'application/json;charset=UTF-8',
      },
      body: JSON.stringify({ receiver_code: receiverCode, provider_code: providerCode }),
    })

    return response.json().then(({ data }: ApiResponse<CreateResponse>) => data)
  },

  getById: async function (depositId: string): Promise<GetByIdResponse> {
    const response = await fetch(`http://localhost:8000/deposit/${depositId}`, {
      method: 'GET',
      headers: { 'content-type': 'application/json;charset=UTF-8' },
    })

    return response.json().then(({ data }: ApiResponse<GetByIdResponse>) => data)
  },

  getByIdAndLineId: async function (
    depositId: string,
    lineId: string,
  ): Promise<GetByIdAndLineIdResponse> {
    const response = await fetch(`http://localhost:8000/deposit/${depositId}/${lineId}`, {
      method: 'GET',
      headers: { 'content-type': 'application/json;charset=UTF-8' },
    })

    return response.json().then(({ data }: ApiResponse<GetByIdAndLineIdResponse>) => data)
  },

  addProduct: async function (depositId: string, productCode: string): Promise<AddProductResponse> {
    const response = await fetch(
      `http://localhost:8000/deposit/${depositId}/return/${productCode}`,
      {
        method: 'GET',
        headers: { 'content-type': 'application/json;charset=UTF-8' },
      },
    )

    return response.json().then(({ data }: ApiResponse<AddProductResponse>) => data)
  },

  cancelProduct: async function (depositId: string, lineId: string): Promise<void> {
    const response = await fetch(`http://localhost:8000/deposit/${depositId}/cancel/${lineId}`, {
      method: 'GET',
      headers: { 'content-type': 'application/json;charset=UTF-8' },
    })

    return response.json().then(({ data }: ApiResponse<void>) => data)
  },

  printTicket: async function (depositId: string): Promise<void> {
    const response = await fetch(`http://localhost:8000/deposit/${depositId}/ticket`, {
      method: 'GET',
      headers: { 'content-type': 'application/json;charset=UTF-8' },
    })

    return response.json().then(({ data }: ApiResponse<void>) => data)
  },

  close: async function (depositId: string): Promise<void> {
    const response = await fetch(`http://localhost:8000/deposit/${depositId}/close`, {
      method: 'GET',
      headers: { 'content-type': 'application/json;charset=UTF-8' },
    })

    return response.json().then(({ data }: ApiResponse<void>) => data)
  },
}
