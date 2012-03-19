
" rpdb2 events "

import signal
import copy
import sys
from rpdb2utils import as_unicode

try:
    import copy_reg
except:
    #
    # The above modules were renamed in Python 3 so try to import them 'as'
    #
    import copyreg as copy_reg



EVENT_EXCLUDE = 'exclude'
EVENT_INCLUDE = 'include'



def calc_signame(signum):
    " Provides the signal name "
    for key, value in vars(signal).items():
        if not key.startswith('SIG') or key in ['SIG_IGN', 'SIG_DFL',
                                                'SIGRTMIN', 'SIGRTMAX']:
            continue

        if value == signum:
            return key

    return '?'


def breakpoint_copy(bp):
    if bp is None:
        return None

    _bp = copy.copy(bp)

    #filename = getFoundUnicodeFiles().get(bp.m_filename, bp.m_filename)

    _bp.m_filename = as_unicode(bp.m_filename, sys.getfilesystemencoding())
    _bp.m_code = None

    return _bp





class CEvent(object):
    " Base class for events "

    def __init__(self):
        pass

    def __reduce__(self):
        return (copy_reg.__newobj__, (type(self), ), vars(self), None, None)

    def is_match(self, arg):
        " 'virtual' method to be oveloaded "
        pass


class CEventNull(CEvent):
    " Sent to release event listeners (Internal, speeds up shutdown) "
    pass


class CEventEmbeddedSync(CEvent):
    """
    Sent when an embedded interpreter becomes active if it needs to 
    determine if there are pending break requests. (Internal)
    """
    pass


class CEventClearSourceCache(CEvent):
    " Sent when the source cache is cleared "
    pass


class CEventSignalIntercepted(CEvent):
    """
    This event is sent when a signal is intercepted inside tracing code.
    Such signals are held pending until tracing code is returned from.
    """
    def __init__(self, signum):
        CEvent.__init__(self)
        self.m_signum = signum
        self.m_signame = calc_signame(signum)
        return


class CEventSignalException(CEvent):
    """
    This event is sent when the handler of a previously intercepted signal
    raises an exception. Such exceptions are ignored because of technical
    limitations.
    """
    def __init__(self, signum, description):
        CEvent.__init__(self)
        self.m_signum = signum
        self.m_signame = calc_signame(signum)
        self.m_description = description
        return


class CEventEncoding(CEvent):
    " The encoding has been set "
    def __init__(self, encoding, fraw):
        CEvent.__init__(self)
        self.m_encoding = encoding
        self.m_fraw = fraw
        return


class CEventPsycoWarning(CEvent):
    " The psyco module was detected. rpdb2 is incompatible with this module "
    pass


class CEventConflictingModules(CEvent):
    """
    Conflicting modules were detected. rpdb2 is incompatible with these modules.
    """
    def __init__(self, modules_list):
        CEvent.__init__(self)
        self.m_modules_list = modules_list
        return


class CEventSyncReceivers(CEvent):
    """
    A base class for events that need to be received by all listeners at
    the same time. The synchronization mechanism is internal to rpdb2.
    """
    def __init__(self, sync_n):
        CEvent.__init__(self)
        self.m_sync_n = sync_n
        return


class CEventForkSwitch(CEventSyncReceivers):
    " Debuggee is about to fork. Try to reconnect. "
    pass


class CEventExecSwitch(CEventSyncReceivers):
    " Debuggee is about to exec. Try to reconnect. "
    pass


class CEventExit(CEvent):
    " Debuggee is terminating "
    pass


class CEventState(CEvent):
    """
    State of the debugger.
    Value of m_state can be one of the STATE_* globals.
    """
    def __init__(self, state):
        CEvent.__init__(self)
        self.m_state = as_unicode(state)
        return

    def is_match(self, arg):
        " True if matched "
        return self.m_state == as_unicode(arg)


class CEventSynchronicity(CEvent):
    """
    Mode of synchronicity.
    Sent when mode changes.
    """
    def __init__(self, fsynchronicity):
        CEvent.__init__(self)
        self.m_fsynchronicity = fsynchronicity
        return

    def is_match(self, arg):
        " True if matched "
        return self.m_fsynchronicity == arg



class CEventTrap(CEvent):
    """
    Mode of "trap unhandled exceptions".
    Sent when the mode changes.
    """
    def __init__(self, ftrap):
        CEvent.__init__(self)
        self.m_ftrap = ftrap
        return

    def is_match(self, arg):
        " True if matched "
        return self.m_ftrap == arg


class CEventForkMode(CEvent):
    """
    Mode of fork behavior has changed.
    Sent when the mode changes.
    """
    def __init__(self, ffork_into_child, ffork_auto):
        CEvent.__init__(self)
        self.m_ffork_into_child = ffork_into_child
        self.m_ffork_auto = ffork_auto
        return


class CEventUnhandledException(CEvent):
    """
    Unhandled Exception
    Sent when an unhandled exception is caught.
    """
    pass


class CEventNamespace(CEvent):
    """
    Namespace has changed.
    This tells the debugger it should query the namespace again.
    """
    pass


class CEventNoThreads(CEvent):
    """
    No threads to debug.
    Debuggee notifies the debugger that it has no threads. This can
    happen in embedded debugging and in a python interpreter session.
    """
    pass


class CEventThreads(CEvent):
    " State of threads "
    def __init__(self, _current_thread, thread_list):
        CEvent.__init__(self)
        self.m_current_thread = _current_thread
        self.m_thread_list = thread_list
        return



class CEventThreadBroken(CEvent):
    " A thread has broken "
    def __init__(self, tid, name):
        CEvent.__init__(self)
        self.m_tid = tid
        self.m_name = as_unicode(name)
        return


class CEventStack(CEvent):
    " Stack of current thread "
    def __init__(self, stack):
        CEvent.__init__(self)
        self.m_stack = stack
        return


class CEventStackFrameChange(CEvent):
    """
    Stack frame has changed.
    This event is sent when the debugger goes up or down the stack.
    """
    def __init__(self, frame_index):
        CEvent.__init__(self)
        self.m_frame_index = frame_index
        return


class CEventStackDepth(CEvent):
    " Stack depth has changed "
    def __init__(self, stack_depth, stack_depth_exception):
        CEvent.__init__(self)
        self.m_stack_depth = stack_depth
        self.m_stack_depth_exception = stack_depth_exception
        return


class CEventBreakpoint(CEvent):
    " A breakpoint or breakpoints changed "

    DISABLE = as_unicode('disable')
    ENABLE = as_unicode('enable')
    REMOVE = as_unicode('remove')
    SET = as_unicode('set')

    def __init__(self, bpoint, action = SET, id_list = [], fAll = False):
        CEvent.__init__(self)
        self.m_bp = breakpoint_copy(bpoint)
        self.m_action = action
        self.m_id_list = id_list
        self.m_fAll = fAll
        return


class CEventSync(CEvent):
    """
    Internal (not sent to the debugger) event that trigers the
    firing of other events that help the debugger synchronize with
    the state of the debuggee.
    """
    def __init__(self, fException, fSendUnhandled):
        CEvent.__init__(self)
        self.m_fException = fException
        self.m_fSendUnhandled = fSendUnhandled
        return



class CEventDispatcher:
    """
    Events dispatcher.
    Dispatchers can be chained together.
    """

    def __init__(self, chained_event_dispatcher = None):
        self.m_chained_event_dispatcher = chained_event_dispatcher
        self.m_chain_override_types = {}

        self.m_registrants = {}
        return


    def shutdown(self):
        " Shutdown "
        for e_rec in list(self.m_registrants.keys()):
            self.remove_dispatcher_record(e_rec)
        return


    def register_callback(self, callback, event_type_dict, fSingleUse):
        " Registers callback "
        e_rec = CEventDispatcherRecord(callback, event_type_dict, fSingleUse)

        #
        # If we have a chained dispatcher, register the callback on the
        # chained dispatcher as well.
        #
        if self.m_chained_event_dispatcher is not None:
            _er = self.__register_callback_on_chain(e_rec,
                                                    event_type_dict,
                                                    fSingleUse)
            self.m_registrants[e_rec] = _er
            return e_rec

        self.m_registrants[e_rec] = True
        return e_rec


    def remove_callback(self, callback):
        " Removes callback "
        erl = [e_rec for e_rec in \
                    list(self.m_registrants.keys()) \
                            if e_rec.m_callback == callback]
        for e_rec in erl:
            self.remove_dispatcher_record(e_rec)
        return


    def fire_events(self, event_list):
        " Fire events "
        for event in event_list:
            self.fire_event(event)
        return


    def fire_event(self, event):
        " Fire event "
        for e_rec in list(self.m_registrants.keys()):
            self.__fire_er(event, e_rec)
        return


    def __fire_er(self, event, e_rec):
        " Fire er? "
        if not e_rec.is_match(event):
            return

        try:
            e_rec.m_callback(event)
        except:
            pass

        if not e_rec.m_fSingleUse:
            return

        try:
            del self.m_registrants[e_rec]
        except KeyError:
            pass
        return


    def register_chain_override(self, event_type_dict):
        """
        Chain override prevents registration on chained 
        dispatchers for specific event types.
        """
        for item in list(event_type_dict.keys()):
            self.m_chain_override_types[item] = True
        return


    def __register_callback_on_chain(self, e_rec, event_type_dict, fSingleUse):
        " Registers callback on chain "
        _event_type_dict = copy.copy(event_type_dict)
        for item in self.m_chain_override_types:
            if item in _event_type_dict:
                del _event_type_dict[item]

        if len(_event_type_dict) == 0:
            return False


        def callback(event, e_rec = e_rec):
            " callback "
            self.__fire_er(event, e_rec)

        _er = self.m_chained_event_dispatcher.register_callback( \
                                                    callback,
                                                    _event_type_dict,
                                                    fSingleUse)
        return _er


    def remove_dispatcher_record(self, e_rec):
        " Removes dispatcher record "
        try:
            if self.m_chained_event_dispatcher is not None:
                _er = self.m_registrants[e_rec]
                if _er != False:
                    self.m_chained_event_dispatcher. \
                                    remove_dispatcher_record(_er)

            del self.m_registrants[e_rec]
        except KeyError:
            pass
        return



class CEventDispatcherRecord:
    """
    Internal structure that binds a callback to particular events.
    """

    def __init__(self, callback, event_type_dict, fSingleUse):
        self.m_callback = callback
        self.m_event_type_dict = copy.copy(event_type_dict)
        self.m_fSingleUse = fSingleUse
        return


    def is_match(self, event):
        " True if matches "
        rtl = [t for t in self.m_event_type_dict.keys() if isinstance(event, t)]
        if len(rtl) == 0:
            return False

        #
        # Examine first match only.
        #

        first = rtl[0]
        rte = self.m_event_type_dict[first].get(EVENT_EXCLUDE, [])
        if len(rte) != 0:
            for evt in rte:
                if event.is_match(evt):
                    return False
            return True

        rte = self.m_event_type_dict[first].get(EVENT_INCLUDE, [])
        if len(rte) != 0:
            for evt in rte:
                if event.is_match(evt):
                    return True
            return False

        return True


