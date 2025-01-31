import { TPreFilters, TAPIFilters, DEFAULT_PRE_FILTERS } from 'core/Bookings'
import {
  formatBrowserTimezonedDateAsUTC,
  FORMAT_ISO_DATE_ONLY,
} from 'utils/date'

export const buildBookingsRecapQuery = ({
  offerVenueId = DEFAULT_PRE_FILTERS.offerVenueId,
  offerEventDate = DEFAULT_PRE_FILTERS.offerEventDate,
  bookingBeginningDate = DEFAULT_PRE_FILTERS.bookingBeginningDate,
  bookingEndingDate = DEFAULT_PRE_FILTERS.bookingEndingDate,
  bookingStatusFilter = DEFAULT_PRE_FILTERS.bookingStatusFilter,
  offerType = DEFAULT_PRE_FILTERS.offerType,
  page,
}: TPreFilters & { page?: number }): TAPIFilters => {
  const params = { page } as TAPIFilters

  if (offerVenueId !== DEFAULT_PRE_FILTERS.offerVenueId) {
    params.venueId = offerVenueId
  }
  if (offerType !== DEFAULT_PRE_FILTERS.offerType) {
    params.offerType = offerType
  }
  if (offerEventDate !== DEFAULT_PRE_FILTERS.offerEventDate) {
    params.eventDate = formatBrowserTimezonedDateAsUTC(offerEventDate)
  }
  if (bookingBeginningDate) {
    params.bookingPeriodBeginningDate = formatBrowserTimezonedDateAsUTC(
      bookingBeginningDate,
      FORMAT_ISO_DATE_ONLY
    )
  }

  if (bookingEndingDate) {
    params.bookingPeriodEndingDate = formatBrowserTimezonedDateAsUTC(
      bookingEndingDate,
      FORMAT_ISO_DATE_ONLY
    )
  }

  params.bookingStatusFilter = bookingStatusFilter

  return params
}
