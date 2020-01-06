import DiscoveryContainer from '../../../../pages/discovery/DiscoveryContainer'
import MyFavoritesContainer from '../../../../pages/my-favorites/MyFavoritesContainer'
import MyBookingsContainer from '../../../../pages/my-bookings/MyBookingsContainer'
import ProfileContainer from '../../../../pages/profile/ProfileContainer'
import SearchContainer from '../../../../pages/search/SearchContainer'
import routes from '../../../../router/routes'
import { getMenuItemsFromRoutes } from '../getMenuItems'
import SearchAlgoliaContainer from '../../../../pages/search-algolia/SearchAlgoliaContainer'

describe('getMenuItemsFromRoutes', () => {
  it('should filter routes for menu from mock', () => {
    const testRoutes = [
      { path: '/' },
      { path: '/toto' },
      { icon: 'toto', path: '/toto/:vars?' },
      { href: '/toto/:vars?', icon: 'toto' },
      { exact: true, path: '/toto/:vars?/vars2?' },
      { icon: 'toto', path: '/toto/:vars?/:vars2?/:vars3?' },
      { href: 'mailto:mail.cool' },
      { href: 'mailto:mail.cool', icon: 'toto' },
    ]
    const items = getMenuItemsFromRoutes(testRoutes)
    const expected = [
      { icon: 'toto', path: '/toto' },
      { href: '/toto/:vars?', icon: 'toto' },
      { icon: 'toto', path: '/toto' },
      { href: 'mailto:mail.cool', icon: 'toto' },
    ]
    expect(items).toStrictEqual(expected)
  })

  it('should filter routes for menu from featured routes', () => {
    // when
    const items = getMenuItemsFromRoutes(routes)
    const expected = [
      {
        component: DiscoveryContainer,
        icon: 'ico-offres',
        path: '/decouverte',
        title: 'Les offres',
      },
      {
        component: SearchContainer,
        icon: 'ico-search',
        path: '/recherche',
        title: 'Recherche',
      },
      {
        component: SearchAlgoliaContainer,
        icon: 'search-w',
        path: '/recherche-algolia',
        featureName: 'SEARCH_ALGOLIA',
        title: 'Recherche algolia',
      },
      {
        component: MyBookingsContainer,
        icon: 'ico-calendar-white',
        path: '/reservations',
        title: 'Mes réservations',
      },
      {
        component: MyFavoritesContainer,
        icon: 'ico-like-empty',
        path: '/favoris',
        title: 'Mes favoris',
      },
      {
        component: ProfileContainer,
        icon: 'ico-user',
        path: '/profil',
        title: 'Mon compte',
      },
      {
        href: 'https://aide.passculture.app/fr/category/18-ans-1dnil5r/',
        icon: 'ico-help',
        target: '_blank',
        title: 'Aide',
      },
      {
        href:
          'https://pass-culture.gitbook.io/documents/textes-normatifs/mentions-legales-et-conditions-generales-dutilisation-de-lapplication-pass-culture',
        icon: 'ico-txt',
        target: '_blank',
        title: 'Mentions légales',
      },
    ]

    // then
    expect(items).toStrictEqual(expected)
  })
})
