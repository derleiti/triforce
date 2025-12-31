---- MODULE MeshGuardian_TTrace_1767118552 ----
EXTENDS Sequences, MeshGuardian, TLCExt, Toolbox, MeshGuardian_TEConstants, Naturals, TLC

_expression ==
    LET MeshGuardian_TEExpression == INSTANCE MeshGuardian_TEExpression
    IN MeshGuardian_TEExpression!expression
----

_trace ==
    LET MeshGuardian_TETrace == INSTANCE MeshGuardian_TETrace
    IN MeshGuardian_TETrace!trace
----

_prop ==
    ~(([]<>(
            restartCount = ([hetzner |-> 2, backup |-> 0])
            /\
            nodeState = ([hetzner |-> "crashed", backup |-> "unhealthy"])
            /\
            guardianActive = (TRUE)
            /\
            failureCount = ([hetzner |-> 3, backup |-> 0])
            /\
            lastHealthCheck = ("backup")
    ))/\([]<>(
            restartCount = ([hetzner |-> 2, backup |-> 0])
            /\
            nodeState = ([hetzner |-> "crashed", backup |-> "healthy"])
            /\
            guardianActive = (TRUE)
            /\
            failureCount = ([hetzner |-> 3, backup |-> 0])
            /\
            lastHealthCheck = ("backup")
    )))
----

_init ==
    /\ lastHealthCheck = _TETrace[1].lastHealthCheck
    /\ guardianActive = _TETrace[1].guardianActive
    /\ restartCount = _TETrace[1].restartCount
    /\ nodeState = _TETrace[1].nodeState
    /\ failureCount = _TETrace[1].failureCount
----

_next ==
    /\ \E i,j \in DOMAIN _TETrace:
        /\ \/ /\ j = i + 1
              /\ i = TLCGet("level")
           \/ /\ i = _TTraceLassoEnd
              /\ j = _TTraceLassoStart
        /\ lastHealthCheck  = _TETrace[i].lastHealthCheck
        /\ lastHealthCheck' = _TETrace[j].lastHealthCheck
        /\ guardianActive  = _TETrace[i].guardianActive
        /\ guardianActive' = _TETrace[j].guardianActive
        /\ restartCount  = _TETrace[i].restartCount
        /\ restartCount' = _TETrace[j].restartCount
        /\ nodeState  = _TETrace[i].nodeState
        /\ nodeState' = _TETrace[j].nodeState
        /\ failureCount  = _TETrace[i].failureCount
        /\ failureCount' = _TETrace[j].failureCount

\* Uncomment the ASSUME below to write the states of the error trace
\* to the given file in Json format. Note that you can pass any tuple
\* to `JsonSerialize`. For example, a sub-sequence of _TETrace.
    \* ASSUME
    \*     LET J == INSTANCE Json
    \*         IN J!JsonSerialize("MeshGuardian_TTrace_1767118552.json", _TETrace)


_view ==
    <<lastHealthCheck, guardianActive, restartCount, nodeState, failureCount, IF TLCGet("level") = _TTraceLassoEnd + 1 THEN _TTraceLassoStart ELSE TLCGet("level")>>
=============================================================================

 Note that you can extract this module `MeshGuardian_TEExpression`
  to a dedicated file to reuse `expression` (the module in the 
  dedicated `MeshGuardian_TEExpression.tla` file takes precedence 
  over the module `MeshGuardian_TEExpression` below).

---- MODULE MeshGuardian_TEExpression ----
EXTENDS Sequences, MeshGuardian, TLCExt, Toolbox, MeshGuardian_TEConstants, Naturals, TLC

expression == 
    [
        \* To hide variables of the `MeshGuardian` spec from the error trace,
        \* remove the variables below.  The trace will be written in the order
        \* of the fields of this record.
        lastHealthCheck |-> lastHealthCheck
        ,guardianActive |-> guardianActive
        ,restartCount |-> restartCount
        ,nodeState |-> nodeState
        ,failureCount |-> failureCount
        
        \* Put additional constant-, state-, and action-level expressions here:
        \* ,_stateNumber |-> _TEPosition
        \* ,_lastHealthCheckUnchanged |-> lastHealthCheck = lastHealthCheck'
        
        \* Format the `lastHealthCheck` variable as Json value.
        \* ,_lastHealthCheckJson |->
        \*     LET J == INSTANCE Json
        \*     IN J!ToJson(lastHealthCheck)
        
        \* Lastly, you may build expressions over arbitrary sets of states by
        \* leveraging the _TETrace operator.  For example, this is how to
        \* count the number of times a spec variable changed up to the current
        \* state in the trace.
        \* ,_lastHealthCheckModCount |->
        \*     LET F[s \in DOMAIN _TETrace] ==
        \*         IF s = 1 THEN 0
        \*         ELSE IF _TETrace[s].lastHealthCheck # _TETrace[s-1].lastHealthCheck
        \*             THEN 1 + F[s-1] ELSE F[s-1]
        \*     IN F[_TEPosition - 1]
    ]

=============================================================================



Parsing and semantic processing can take forever if the trace below is long.
 In this case, it is advised to uncomment the module below to deserialize the
 trace from a generated binary file.

\*
\*---- MODULE MeshGuardian_TETrace ----
\*EXTENDS IOUtils, MeshGuardian, MeshGuardian_TEConstants, TLC
\*
\*trace == IODeserialize("MeshGuardian_TTrace_1767118552.bin", TRUE)
\*
\*=============================================================================
\*

---- MODULE MeshGuardian_TETrace ----
EXTENDS MeshGuardian, MeshGuardian_TEConstants, TLC

trace == 
    <<
    ([restartCount |-> [hetzner |-> 0, backup |-> 0],nodeState |-> [hetzner |-> "healthy", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 0, backup |-> 0],lastHealthCheck |-> "-"]),
    ([restartCount |-> [hetzner |-> 0, backup |-> 0],nodeState |-> [hetzner |-> "unhealthy", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 0, backup |-> 0],lastHealthCheck |-> "-"]),
    ([restartCount |-> [hetzner |-> 0, backup |-> 0],nodeState |-> [hetzner |-> "unhealthy", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 1, backup |-> 0],lastHealthCheck |-> "hetzner"]),
    ([restartCount |-> [hetzner |-> 0, backup |-> 0],nodeState |-> [hetzner |-> "unhealthy", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 2, backup |-> 0],lastHealthCheck |-> "hetzner"]),
    ([restartCount |-> [hetzner |-> 0, backup |-> 0],nodeState |-> [hetzner |-> "unhealthy", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 3, backup |-> 0],lastHealthCheck |-> "hetzner"]),
    ([restartCount |-> [hetzner |-> 1, backup |-> 0],nodeState |-> [hetzner |-> "restarting", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 0, backup |-> 0],lastHealthCheck |-> "hetzner"]),
    ([restartCount |-> [hetzner |-> 1, backup |-> 0],nodeState |-> [hetzner |-> "healthy", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 0, backup |-> 0],lastHealthCheck |-> "hetzner"]),
    ([restartCount |-> [hetzner |-> 1, backup |-> 0],nodeState |-> [hetzner |-> "unhealthy", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 0, backup |-> 0],lastHealthCheck |-> "hetzner"]),
    ([restartCount |-> [hetzner |-> 1, backup |-> 0],nodeState |-> [hetzner |-> "unhealthy", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 1, backup |-> 0],lastHealthCheck |-> "hetzner"]),
    ([restartCount |-> [hetzner |-> 1, backup |-> 0],nodeState |-> [hetzner |-> "unhealthy", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 2, backup |-> 0],lastHealthCheck |-> "hetzner"]),
    ([restartCount |-> [hetzner |-> 1, backup |-> 0],nodeState |-> [hetzner |-> "unhealthy", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 3, backup |-> 0],lastHealthCheck |-> "hetzner"]),
    ([restartCount |-> [hetzner |-> 2, backup |-> 0],nodeState |-> [hetzner |-> "restarting", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 0, backup |-> 0],lastHealthCheck |-> "hetzner"]),
    ([restartCount |-> [hetzner |-> 2, backup |-> 0],nodeState |-> [hetzner |-> "restarting", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 1, backup |-> 0],lastHealthCheck |-> "hetzner"]),
    ([restartCount |-> [hetzner |-> 2, backup |-> 0],nodeState |-> [hetzner |-> "restarting", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 2, backup |-> 0],lastHealthCheck |-> "hetzner"]),
    ([restartCount |-> [hetzner |-> 2, backup |-> 0],nodeState |-> [hetzner |-> "healthy", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 2, backup |-> 0],lastHealthCheck |-> "hetzner"]),
    ([restartCount |-> [hetzner |-> 2, backup |-> 0],nodeState |-> [hetzner |-> "crashed", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 2, backup |-> 0],lastHealthCheck |-> "hetzner"]),
    ([restartCount |-> [hetzner |-> 2, backup |-> 0],nodeState |-> [hetzner |-> "crashed", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 3, backup |-> 0],lastHealthCheck |-> "hetzner"]),
    ([restartCount |-> [hetzner |-> 2, backup |-> 0],nodeState |-> [hetzner |-> "crashed", backup |-> "healthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 3, backup |-> 0],lastHealthCheck |-> "backup"]),
    ([restartCount |-> [hetzner |-> 2, backup |-> 0],nodeState |-> [hetzner |-> "crashed", backup |-> "unhealthy"],guardianActive |-> TRUE,failureCount |-> [hetzner |-> 3, backup |-> 0],lastHealthCheck |-> "backup"])
    >>
----


=============================================================================

---- MODULE MeshGuardian_TEConstants ----
EXTENDS MeshGuardian

CONSTANTS _TTraceLassoStart, _TTraceLassoEnd

=============================================================================

---- CONFIG MeshGuardian_TTrace_1767118552 ----
CONSTANTS
    Nodes = { "hetzner" , "backup" }
    MaxFailures = 3
    MaxRestarts = 2
_TTraceLassoStart = 18
_TTraceLassoEnd = 19

PROPERTY
    _prop

CHECK_DEADLOCK
    \* CHECK_DEADLOCK off because of PROPERTY or INVARIANT above.
    FALSE

INIT
    _init

NEXT
    _next

VIEW
    _view

CONSTANT
    _TETrace <- _trace

ALIAS
    _expression
=============================================================================
\* Generated on Tue Dec 30 19:15:52 CET 2025