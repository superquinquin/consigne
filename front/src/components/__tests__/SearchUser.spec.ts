import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import SearchUser from '../SearchUser.vue'
import UsersProvider, { type SearchUserResponse } from '@/services/users'
import type { ApiResponse } from '@/services/api.utils'

const mountWithMatches = (
  searchUser: () => Promise<ApiResponse<SearchUserResponse>>,
) =>
  mount(SearchUser, {
    global: {
      provide: {
        UsersProvider: { ...UsersProvider, searchUser },
      },
    },
  })

const okResponse = (matches: [number, number, string][]) =>
  Promise.resolve({ status: 200, reasons: 'OK', data: { matches } })

const submitSearch = async (wrapper: ReturnType<typeof mountWithMatches>, input: string) => {
  await wrapper.find('input').setValue(input)
  await wrapper.find('button').trigger('click')
  await new Promise((resolve) => setTimeout(resolve))
  await wrapper.vm.$nextTick()
}

describe('SearchUser', () => {
  it('warns the operator when the search succeeds but returns no cooperator', async () => {
    const wrapper = mountWithMatches(() => okResponse([]))

    await submitSearch(wrapper, 'inconnu')

    expect(wrapper.text()).toContain('Aucun coopérateur ne correspond')
    expect(wrapper.text()).toContain('inconnu')
    expect(wrapper.findComponent({ name: 'UserCard' }).exists()).toBe(false)
  })

  it('renders the matches and no warning when the search returns cooperators', async () => {
    const wrapper = mountWithMatches(() => okResponse([[1111, 1615, '1615 - BAGLIN, Marine']]))

    await submitSearch(wrapper, 'baglin')

    expect(wrapper.text()).not.toContain('Aucun coopérateur ne correspond')
    expect(wrapper.text()).toContain('BAGLIN')
  })

  it('reports an error, not an empty result, when the api answers without matches', async () => {
    const wrapper = mountWithMatches(() =>
      Promise.resolve({ status: 500, reasons: 'KO', data: {} } as ApiResponse<SearchUserResponse>),
    )

    await submitSearch(wrapper, 'baglin')

    expect(wrapper.text()).toContain('La recherche a échoué')
    expect(wrapper.text()).not.toContain('Aucun coopérateur ne correspond')
  })

  it('warns the operator when the search itself fails', async () => {
    const wrapper = mountWithMatches(() => Promise.reject(new Error('network down')))

    await submitSearch(wrapper, 'baglin')

    expect(wrapper.text()).toContain('La recherche a échoué')
  })

  it('does not search nor warn on an empty input', async () => {
    const wrapper = mountWithMatches(() => okResponse([]))

    await wrapper.find('button').trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).not.toContain('Aucun coopérateur ne correspond')
    expect(wrapper.find('button').attributes('disabled')).toBeUndefined()
  })
})
