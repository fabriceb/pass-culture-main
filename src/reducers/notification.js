export const CLOSE_NOTIFICATION = 'CLOSE_NOTIFICATION'
export const SHOW_NOTIFICATION = 'SHOW_NOTIFICATION'

// INITIAL STATE
const initialState = null

// REDUCER
function notification(state = initialState, action) {
  switch (action.type) {
    case CLOSE_NOTIFICATION:
      return initialState
    case SHOW_NOTIFICATION:
      return action.notification
    default:
      return state
  }
}

// ACTION CREATORS
export function closeNotification(notification) {
  return {
    type: CLOSE_NOTIFICATION
  }
}

export function showNotification(notification) {
  return {
    type: SHOW_NOTIFICATION,
    notification,
  }
}

// default
export default notification
