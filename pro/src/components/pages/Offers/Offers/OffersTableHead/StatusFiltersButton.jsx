import PropTypes from 'prop-types'
import React, { Fragment, useState } from 'react'

import Icon from 'components/layout/Icon'
import {
  ADMINS_DISABLED_FILTERS_MESSAGE,
  OFFER_STATUS_LIST,
} from 'core/Offers/constants'

import { OffersStatusFiltersModal } from '../OffersStatusFiltersModal/OffersStatusFiltersModal'

const StatusFiltersButton = ({
  disabled,
  applyFilters,
  status,
  updateStatusFilter,
}) => {
  const [isStatusFiltersVisible, setIsStatusFiltersVisible] = useState(false)

  const isFilteredByStatus = OFFER_STATUS_LIST.includes(status)

  function toggleStatusFiltersVisibility() {
    setIsStatusFiltersVisible(!isStatusFiltersVisible)
  }

  return (
    <Fragment>
      <button
        disabled={disabled}
        onClick={toggleStatusFiltersVisibility}
        title={disabled ? ADMINS_DISABLED_FILTERS_MESSAGE : undefined}
        type="button"
      >
        Statut
        <Icon
          alt="Afficher ou masquer le filtre par statut"
          className={isFilteredByStatus ? 'active-status-filter' : undefined}
          svg={
            isFilteredByStatus
              ? 'ico-filter-status-active'
              : 'ico-filter-status-red'
          }
        />
      </button>
      <OffersStatusFiltersModal
        applyFilters={applyFilters}
        isVisible={isStatusFiltersVisible}
        setIsVisible={setIsStatusFiltersVisible}
        status={status}
        updateStatusFilter={updateStatusFilter}
      />
    </Fragment>
  )
}

export default StatusFiltersButton

StatusFiltersButton.defaultProps = {
  disabled: false,
  status: null,
}

StatusFiltersButton.propTypes = {
  applyFilters: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  status: PropTypes.string,
  updateStatusFilter: PropTypes.func.isRequired,
}
