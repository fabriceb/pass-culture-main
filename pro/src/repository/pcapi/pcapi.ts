/*
 * @debt complexity "Gaël: the file contains eslint error(s) based on our new config"
 */

import { DEFAULT_PRE_FILTERS } from 'components/pages/Bookings/PreFilters/_constants'
import {
  ALL_OFFERERS,
  DEFAULT_SEARCH_FILTERS,
} from 'components/pages/Offers/Offers/_constants'
import { DEFAULT_INVOICES_FILTERS } from 'components/pages/Reimbursements/_constants'
import {
  DeepPartialEducationalOfferModelPayload,
  EducationalOfferModelPayload,
} from 'core/OfferEducational'
import {
  EducationalOfferer,
  Feature,
  Offer,
  Offerer,
  OffererListItem,
  OffererName,
  Venue,
  VenueListItem,
  VenueStats,
} from 'custom_types'
import { client } from 'repository/pcapi/pcapiClient'
import {
  FORMAT_ISO_DATE_ONLY,
  formatBrowserTimezonedDateAsUTC,
} from 'utils/date'
import { stringify } from 'utils/query-string'

export const loadFeatures = async (): Promise<Feature[]> => {
  return client.get('/features')
}

//
// offers
//
export const loadOffer = async (offerId: string): Promise<Offer> => {
  return client.get(`/offers/${offerId}`)
}

// TODO: type offer payload
// eslint-disable-next-line
export const createOffer = (offer: Record<string, any>): Promise<{ id: string }> => {
  return client.post(`/offers`, offer)
}

export const createEducationalOffer = (
  offer: EducationalOfferModelPayload
): Promise<{ id: string }> => client.post('/offers/educational', offer)

export const updateOffer = (
  offerId: string,
  // TODO: type offer payload
  // eslint-disable-next-line
  offer: Record<string, any>
): Promise<{ id: string }> => {
  return client.patch(`/offers/${offerId}`, offer)
}

export const updateEducationalOffer = (
  offerId: string,
  offer: DeepPartialEducationalOfferModelPayload
): Promise<Offer> => client.patch(`/offers/educational/${offerId}`, offer)

export const loadFilteredOffers = async ({
  nameOrIsbn = DEFAULT_SEARCH_FILTERS.nameOrIsbn,
  offererId = DEFAULT_SEARCH_FILTERS.offererId,
  venueId = DEFAULT_SEARCH_FILTERS.venueId,
  categoryId = DEFAULT_SEARCH_FILTERS.categoryId,
  periodBeginningDate = DEFAULT_SEARCH_FILTERS.periodBeginningDate,
  periodEndingDate = DEFAULT_SEARCH_FILTERS.periodEndingDate,
  status = DEFAULT_SEARCH_FILTERS.status,
  creationMode = DEFAULT_SEARCH_FILTERS.creationMode,
}: {
  nameOrIsbn?: string
  offererId?: string
  venueId?: string
  categoryId?: string
  periodBeginningDate?: string
  periodEndingDate?: string
  status?: string
  creationMode?: string
}): Promise<Offer[]> => {
  const body = createRequestBody({
    nameOrIsbn,
    offererId,
    venueId,
    categoryId,
    status,
    creationMode,
    periodBeginningDate,
    periodEndingDate,
  })

  const queryParams = stringify(body)
  return client.get(`/offers${queryParams ? `?${queryParams}` : ''}`)
}

export const updateOffersActiveStatus = (
  areAllOffersSelected: boolean,
  {
    name = undefined,
    offererId = DEFAULT_SEARCH_FILTERS.offererId,
    venueId = DEFAULT_SEARCH_FILTERS.venueId,
    categoryId = DEFAULT_SEARCH_FILTERS.categoryId,
    status = DEFAULT_SEARCH_FILTERS.status,
    creationMode = DEFAULT_SEARCH_FILTERS.creationMode,
    ids = [],
    isActive,
    periodBeginningDate = DEFAULT_SEARCH_FILTERS.periodBeginningDate,
    periodEndingDate = DEFAULT_SEARCH_FILTERS.periodEndingDate,
  }: {
    name?: string
    offererId?: string
    venueId?: string
    categoryId?: string
    status?: string
    creationMode?: string
    ids?: string[]
    isActive?: boolean
    periodBeginningDate?: string
    periodEndingDate?: string
  }
): Promise<void> => {
  const formattedBody = createRequestBody({
    name,
    offererId,
    venueId,
    categoryId,
    status,
    creationMode,
    periodBeginningDate,
    periodEndingDate,
  })

  if (areAllOffersSelected) {
    return client.patch('/offers/all-active-status', {
      ...formattedBody,
      isActive,
    })
  }

  return client.patch('/offers/active-status', { ids, isActive })
}

const createRequestBody = (
  searchFilters: Record<string, string | undefined>
) => {
  const body = {} as Record<string, string | undefined>
  Object.keys(DEFAULT_SEARCH_FILTERS).forEach(field => {
    if (
      searchFilters[field] &&
      // @ts-expect-error field may not be a key of DEFAULT_SEARCH_FILTERS
      searchFilters[field] !== DEFAULT_SEARCH_FILTERS[field]
    ) {
      body[field] = searchFilters[field]
    }
  })

  if (searchFilters.page) {
    body.page = searchFilters.page
  }

  if (
    searchFilters.periodBeginningDate !==
    DEFAULT_SEARCH_FILTERS.periodBeginningDate
  ) {
    body.periodBeginningDate = searchFilters.periodBeginningDate
  }

  if (
    searchFilters.periodEndingDate !== DEFAULT_SEARCH_FILTERS.periodEndingDate
  ) {
    body.periodEndingDate = searchFilters.periodEndingDate
  }

  return body
}

//
// offerers
//

export const getAllOfferersNames = async (): Promise<OffererName[]> => {
  return client.get('/offerers/names').then(response => response.offerersNames)
}

export const generateOffererApiKey = async (
  offererId: string
): Promise<string> => {
  return client
    .post(`/offerers/${offererId}/api_keys`, {})
    .then(response => response.apiKey)
}

export const deleteOffererApiKey = async (apiKey: string): Promise<void> => {
  return client.delete(`/offerers/api_keys/${apiKey}`)
}

export const getUserValidatedOfferersNames = async (): Promise<
  OffererName[]
> => {
  return client
    .get('/offerers/names?validated_for_user=true')
    .then(response => response.offerersNames)
}

export const getValidatedOfferersNames = (): Promise<OffererName[]> => {
  return client
    .get('/offerers/names?validated=true')
    .then(response => response.offerersNames)
}

export const getOfferers = (): Promise<OffererListItem[]> => {
  return client.get('/offerers')
}

export const getValidatedOfferers = (): Promise<OffererListItem[]> => {
  return client.get('/offerers?validated=true')
}

export const getOfferer = (offererId: string): Promise<Offerer> => {
  return client.get(`/offerers/${offererId}`)
}

export const canOffererCreateEducationalOffer = (
  offererId: string
): Promise<void> => client.get(`/offerers/${offererId}/eac-eligibility`)

export const getEducationalOfferers = (
  offererId: string
): Promise<{ educationalOfferers: EducationalOfferer[] }> => {
  const queryParams = `${offererId ? `?offerer_id=${offererId}` : ''}`
  return client.get(`/offerers/educational${queryParams}`)
}

//
// venues
//
export const getVenuesForOfferer = async ({
  offererId,
  activeOfferersOnly = false,
}: {
  offererId?: string
  activeOfferersOnly?: boolean
} = {}): Promise<VenueListItem[]> => {
  const request = {} as {
    offererId: string
    validatedForUser: boolean
    activeOfferersOnly: boolean
  }
  if (offererId) {
    if (offererId !== ALL_OFFERERS) request.offererId = offererId
  } else {
    request.validatedForUser = true
  }

  if (activeOfferersOnly) request.activeOfferersOnly = true
  const queryParams = stringify(request)
  const url = queryParams !== '' ? `/venues?${queryParams}` : '/venues'
  return client.get(url).then(response => response.venues)
}

export const getVenue = (venueId: string): Promise<Venue> =>
  client.get(`/venues/${venueId}`)

export const getVenueStats = (venueId: string): Promise<VenueStats> =>
  client.get(`/venues/${venueId}/stats`)

export const postImageToVenue = async ({
  venueId,
  banner,
  xCropPercent,
  yCropPercent,
  heightCropPercent,
}: {
  venueId: string
  banner: File | undefined
  xCropPercent: number
  yCropPercent: number
  heightCropPercent: number
}): Promise<Venue> => {
  const body = new FormData()
  if (banner) {
    body.append('banner', banner)
  }

  const queryParams = stringify({
    x_crop_percent: xCropPercent,
    y_crop_percent: yCropPercent,
    height_crop_percent: heightCropPercent,
  })

  return await client.postWithFormData(
    `/venues/${venueId}/banner?${queryParams}`,
    body
  )
}

//
// categories
//
export const loadCategories = async (): Promise<{
  categories: Category[]
  subcategories: SubCategory[]
}> => {
  return client.get('/offers/categories')
}

//
// stocks
//
export const loadStocks = offerId => {
  return client.get(`/offers/${offerId}/stocks`)
}

export const bulkCreateOrEditStock = (offerId, stocks) => {
  return client.post(`/stocks/bulk`, {
    offerId,
    stocks,
  })
}

export const deleteStock = stockId => {
  return client.delete(`/stocks/${stockId}`)
}

export const createEducationalStock = stock => {
  return client.post(`/stocks/educational`, stock)
}

export const createEducationalShadowStock = (offerId, stock) =>
  client.post(`/offers/educational/${offerId}/shadow-stock`, stock)

export const editEducationalStock = (stockId, stock) => {
  return client.patch(`/stocks/educational/${stockId}`, stock)
}

export const cancelEducationalBooking = offerId => {
  return client.patch(`/offers/${offerId}/cancel_booking`)
}

export const transformShadowStockIntoEducationalStock = (stockId, stock) =>
  client.patch(`/stocks/shadow-to-educational/${stockId}`, stock)

export const editShadowStock = (stockId, stock) =>
  client.patch(`/stocks/shadow/${stockId}`, stock)

//
// thumbnail
//
export const validateDistantImage = url => {
  return client.post('/offers/thumbnail-url-validation', { url: url })
}

export const postThumbnail = (
  offerId,
  credit,
  thumb,
  thumbUrl,
  x,
  y,
  height
) => {
  const body = new FormData()
  body.append('offerId', offerId)
  body.append('credit', credit)
  body.append('croppingRectX', x)
  body.append('croppingRectY', y)
  body.append('croppingRectHeight', height)
  body.append('thumb', thumb)
  body.append('thumbUrl', thumbUrl)

  return client.postWithFormData('/offers/thumbnails', body)
}

//
// user
//
export const signout = () => client.get('/users/signout')

export const updateUserInformations = body => {
  return client.patch('/users/current', body)
}

export const getUserInformations = () => {
  return client.get('/users/current')
}

//
// set password
//
export const setPassword = (token, newPassword) => {
  return client.post('/users/new-password', { token, newPassword })
}

//
// tutos
//
export const setHasSeenTutos = () => {
  return client.patch(`/users/tuto-seen`)
}

//
// Providers
//
export const createVenueProvider = async venueProvider => {
  return client.post('/venueProviders', venueProvider)
}

export const editVenueProvider = async venueProvider => {
  return client.put('/venueProviders', venueProvider)
}

export const loadProviders = async venueId => {
  return client.get(`/providers/${venueId}`)
}

export const loadVenueProviders = async venueId => {
  return client
    .get(`/venueProviders?venueId=${venueId}`)
    .then(response => response.venue_providers)
}

//
// BookingsRecap
//
export const buildBookingsRecapQuery = ({
  venueId = DEFAULT_PRE_FILTERS.offerVenueId,
  eventDate = DEFAULT_PRE_FILTERS.offerEventDate,
  bookingPeriodBeginningDate = DEFAULT_PRE_FILTERS.bookingBeginningDate,
  bookingPeriodEndingDate = DEFAULT_PRE_FILTERS.bookingEndingDate,
  bookingStatusFilter = DEFAULT_PRE_FILTERS.bookingStatusFilter,
  offerType = DEFAULT_PRE_FILTERS.offerType,
  page,
}) => {
  const params = { page }

  if (venueId !== DEFAULT_PRE_FILTERS.offerVenueId) {
    params.venueId = venueId
  }
  if (offerType !== DEFAULT_PRE_FILTERS.offerType) {
    params.offerType = offerType
  }
  if (eventDate !== DEFAULT_PRE_FILTERS.offerEventDate) {
    params.eventDate = formatBrowserTimezonedDateAsUTC(eventDate)
  }
  params.bookingPeriodBeginningDate = formatBrowserTimezonedDateAsUTC(
    bookingPeriodBeginningDate,
    FORMAT_ISO_DATE_ONLY
  )
  params.bookingPeriodEndingDate = formatBrowserTimezonedDateAsUTC(
    bookingPeriodEndingDate,
    FORMAT_ISO_DATE_ONLY
  )

  params.bookingStatusFilter = bookingStatusFilter

  return stringify(params)
}

export const loadFilteredBookingsRecap = async filters => {
  const queryParams = buildBookingsRecapQuery(filters)
  return client.get(`/bookings/pro?${queryParams}`)
}

export const getFilteredBookingsCSV = async filters => {
  const queryParams = buildBookingsRecapQuery(filters)
  return client.getPlainText(`/bookings/csv?${queryParams}`)
}

//
// Booking
//

export const getBooking = code => {
  return client.get(`/v2/bookings/token/${code}`)
}

export const validateBooking = code => {
  return client.patch(`/v2/bookings/use/token/${code}`)
}

export const invalidateBooking = code => {
  return client.patch(`/v2/bookings/keep/token/${code}`)
}

//
// Business Unit
//

export const getBusinessUnits = offererId => {
  const queryParams = offererId ? `?offererId=${offererId}` : ''

  return client.get(`/finance/business-units${queryParams}`)
}

export const editBusinessUnit = (businessUnitId, siret) => {
  return client.patch(`/finance/business-units/${businessUnitId}`, {
    siret: siret,
  })
}

//
// Invoices
//

const buildInvoicesQuery = ({
  businessUnitId = DEFAULT_INVOICES_FILTERS.businessUnitId,
  periodBeginningDate = DEFAULT_INVOICES_FILTERS.periodBeginningDate,
  periodEndingDate = DEFAULT_INVOICES_FILTERS.periodEndingDate,
}) => {
  const params = {}
  if (businessUnitId !== DEFAULT_INVOICES_FILTERS.businessUnitId) {
    params.businessUnitId = businessUnitId
  }

  if (periodBeginningDate !== DEFAULT_INVOICES_FILTERS.periodBeginningDate) {
    params.periodBeginningDate = formatBrowserTimezonedDateAsUTC(
      periodBeginningDate,
      FORMAT_ISO_DATE_ONLY
    )
  }

  if (periodEndingDate !== DEFAULT_INVOICES_FILTERS.periodEndingDate) {
    params.periodEndingDate = formatBrowserTimezonedDateAsUTC(
      periodEndingDate,
      FORMAT_ISO_DATE_ONLY
    )
  }

  return stringify(params)
}

export const getInvoices = async params => {
  const queryParams = buildInvoicesQuery(params)
  return client.get(`/finance/invoices?${queryParams}`)
}
