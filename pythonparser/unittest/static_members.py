
class C:
    s_member1 = 100
    s_member2, s_member3 = 11, 12

    def f( self ):
        pass

    (s_member4, s_member5, s_member6) = (1, 2, 3)

    # static member usage
    s_member1 = 16 - 13

    def g( self ):
        pass

class D:

    class E:
        s_mem_e1 = 733
        def f():
            class F:
                s_mem_f1 = "kkk"
                def g():
                    pass
                s_mem_f2 = "ttt"
            pass
        s_mem_e2 = "733"

    def h():
        pass

