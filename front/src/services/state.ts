import { reactive } from 'vue'
import type { User } from './users'

export type Provider = User
export type Receiver = User

const GLOBAL_STATE_KEY = 'SQQ_CONSIGNE_GLOBAL_STATE'

const globalState = reactive<{
  provider?: Provider
  receiver?: Receiver
  depositId?: number
}>({})


export function getGlobalState() {
  const storedState: typeof globalState = JSON.parse(localStorage.getItem(GLOBAL_STATE_KEY) || '{}')
  if(storedState.provider === globalState.provider && storedState.receiver === globalState.receiver && storedState.depositId === globalState.depositId) {
    return globalState
  }else {
    setGlobalState(storedState)
  }

  return globalState
}

export function setGlobalState(state: typeof globalState) {
  globalState.provider = state.provider
  globalState.receiver = state.receiver
  globalState.depositId = state.depositId

  localStorage.setItem(GLOBAL_STATE_KEY, JSON.stringify(globalState))
}
