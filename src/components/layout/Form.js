import debounce from 'lodash.debounce'
import get from 'lodash.get'
import { requestData } from 'pass-culture-shared'
import PropTypes from 'prop-types'
import React, {Component} from 'react'
import { connect } from 'react-redux'

import { newMergeForm } from '../../reducers/form'
import { removeErrors } from '../../reducers/errors'
import { recursiveMap } from '../../utils/react'
import { pluralize } from '../../utils/string'

class Form extends Component {

  constructor(props) {
    super(props)
    this.state = {
      editedValues: {},
    }
    this.onDebouncedMergeForm = debounce(
      this.onMergeForm,
      props.debounceTimeout
    )
  }

  static defaultProps = {
    TagName: 'form',
    formData: {},
    formErrors: {},
    debounceTimeout: 300,
    formatData: data => data,
  }

  static propTypes = {
    name: PropTypes.string.isRequired,
    action : PropTypes.string.isRequired,
    data: PropTypes.object,
  }

  static getDerivedStateFromProps = (props, prevState) => {
    return {
      method: props.method || get(props, 'data.id') ? 'PATCH' : 'POST',
    }
  }

  onMergeForm = () => {
    // this.props.removeErrors()
    this.props.newMergeForm(this.props.name, this.state.editedValues)
    this.setState({
      editedValues: {},
    })
  }

  onSubmit = e => {
    e.preventDefault()
    const {
      action,
      formData,
      formatData,
      handleFail,
      handleSuccess,
      name,
      requestData,
      storePath,
    } = this.props

    requestData(
      this.state.method,
      action.replace(/^\//g, ''), {
      body: formatData(formData),
      formName: name,
      handleFail,
      handleSuccess,
      key: storePath, // key is a reserved prop name
      encode: formData instanceof FormData ? 'multipart/form-data' : null,
    })
  }

  updateFormValue = (key, value) => {
    this.setState({
      editedValues: Object.assign(this.state.editedValues, {[key]: value})
    })
    // Using debounce makes it fail when fields depends on each other (venue and offerer in OccasionForm)
    // TODO: find a fix
    // this.onDebouncedMergeForm()
    this.onMergeForm()
  }

  childrenWithProps = () => {
    const {
      children,
      formData,
      formErrors,
      data: storeData,
      layout,
      name,
      readOnly,
      size,
    } = this.props
    let requiredFields = []

    return recursiveMap(children, c => {
      if (c.type.displayName === 'Field') {
        if (c.props.required) {
          requiredFields = requiredFields.concat(c)
        }
        const formValue = get(formData || {}, c.props.name)
        const storeValue = get(storeData || {}, c.props.name)

        return React.cloneElement(c, {
          id: `${name}-${c.props.name}`,
          onChange: this.updateFormValue,
          value: formValue || storeValue || '',
          errors: [].concat(formErrors).filter(e => get(e, c.props.name)).map(e => get(e, c.props.name)),
          readOnly: c.props.readOnly || readOnly,
          layout,
          size,
        })
      } else if (c.type.displayName === 'Submit') {
        return React.cloneElement(c, Object.assign({
          name,
          getDisabled: () => {
            const missingFields = requiredFields.filter(f => !get(formData, `${f.props.name}`))
            return missingFields.length > 0
          },
          getTitle: () => {
            const missingFields = requiredFields.filter(f => !get(formData, `${f.props.name}`))
            if (missingFields.length === 0) return
            return `Champs ${pluralize('non-valide', missingFields.length)} : ${missingFields.map(f => (f.props.label || f.props.title || '').toLowerCase()).join(', ')}`
          }
        }, this.props.TagName !== 'form' ? {
          // If not a real form, need to mimic the submit behavior
          onClick: this.onSubmit,
          type: 'button',
        } : {}))
      }
      return c
    })
  }

  render() {
    const {
      action,
      className,
      name,
      TagName,
    } = this.props
    const {
      method
    } = this.state
    return (
      <TagName
        action={action}
        className={className}
        id={name}
        method={method}
        onSubmit={this.onSubmit}
      >
        {this.childrenWithProps()}
      </TagName>
    )
  }

}

export default connect(
  (state, ownProps) => ({
    formData: get(state, `form.${ownProps.name}.data`),
    formErrors: get(state, `form.${ownProps.name}.errors`),
  }),
  { newMergeForm, removeErrors, requestData }
)(Form)
