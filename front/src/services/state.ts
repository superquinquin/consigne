import { reactive } from 'vue'
import type { User } from './users'

export type Provider = User
export type Receiver = User

export const globalState = reactive<{
  provider?: Provider
  receiver?: Receiver
  depositId?: number
}>({})
