import get from 'lodash.get'
import classnames from 'classnames'
import PropTypes from 'prop-types'
import React, { Component } from 'react'
import { connect } from 'react-redux'

import { requestData } from '../../reducers/data'
// import { FAIL, PENDING, SUCCESS } from '../../reducers/queries'
import { randomHash } from '../../utils/random'

class SubmitButton extends Component {
  constructor() {
    super()
    this.state = {
      submitRequestId: null,
      submitRequestStatus: null
    }
  }

  onSubmitClick = event => {
    if (this.state.submitRequestId) return
    event.preventDefault()
    const {
      add,
      form,
      getBody,
      getOptimistState,
      getSuccessState,
      method,
      onClick,
      path,
      storeKey,
      requestData,
      isNotification,
      getNotification
    } = this.props
    const submitRequestId = randomHash()
    this.setState({
      submitRequestId,
    })
    requestData(method, path, {
      add,
      body: (getBody && getBody(form)) || form,
      getOptimistState,
      getSuccessState,
      key: storeKey,
      requestId: submitRequestId,
      isNotification,
      getNotification
    })
    onClick && onClick()
  }

  static getDerivedStateFromProps(nextProps, prevState) {
    if (prevState.submitRequestId) {
      const returnedQuery = nextProps.queries.find(
        q => q.id === prevState.submitRequestId
      )
      const submitRequestId = get(returnedQuery, 'status', '') === 'PENDING'
        ? returnedQuery.id
        : null
      return {
        submitRequestStatus: get(returnedQuery, 'status'),
        submitRequestId
      }
    }
    return null
  }

  componentDidUpdate (prevProps, prevState) {
    const { handleStatusChange } = this.props
    const { submitRequestStatus } = this.state
    if (prevState.submitRequestStatus !== submitRequestStatus) {
      handleStatusChange && handleStatusChange(submitRequestStatus)
    }
  }

  render() {
    const { className, getIsDisabled, form, text, submittingText } = this.props
    const { submitRequestId } = this.state
    const isDisabled = getIsDisabled(form)
    return (
      <button
        className={classnames(className, {
          disabled: isDisabled,
        })}
        disabled={Boolean(submitRequestId) || isDisabled}
        onClick={this.onSubmitClick}
      >
        {submitRequestId ? submittingText : text}
      </button>
    )
  }
}

SubmitButton.defaultProps = {
  className: 'button',
  getBody: form => form,
  getIsDisabled: form => Object.keys(form).length === 0,
  method: 'POST',
  text: 'Soumettre',
  submittingText: 'Envoi ...',
}

SubmitButton.propTypes = {
  path: PropTypes.string.isRequired,
}

export default connect(
  ({ form, queries }) => ({
    form,
    queries,
  }),
  { requestData }
)(SubmitButton)
