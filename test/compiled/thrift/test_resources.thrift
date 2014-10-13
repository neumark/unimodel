namespace py test_resources.py

struct SomeStruct {
    1: optional string company,
    2: optional string ipaddress,
    3: optional i64 timestamp,
    4: optional bool notified
}

typedef string Application

typedef list<map<Application, list<SomeStruct>>> TDL

const TDL default_blacklist = [
    {
        "mediaservice": [
                {'company': "reuse", 'ipaddress': "127.0.0.1", 'timestamp': 0, 'notified': false},
                {'company': "dynapps", 'ipaddress': "127.0.0.1", 'timestamp': 1000, 'notified': true}
        ],
        "presentationservice": [
                {'company': "dropbox", 'ipaddress': "158.3.4.5", 'timestamp': 0, 'notified': true}
        ]
    },
    {
        "storageproxy": [
                    {'company': "keynote", 'ipaddress': "148.23.45.5", 'timestamp': 2342342, 'notified': false}
        ]
    }
]

struct A {
    1: i64 a,
    2: SomeStruct c,
    3: i64 d=6,
    4: list<string> e,
    5: list<SomeStruct> f
    6: map<i64, string> g
    7: list<map<i64, list<SomeStruct>>> h
}

union B {
    1: i64 a,
    2: string b
}

enum T {
    ADD = 1,
    SUB = 2
}

struct C {
  1: required B b,
  2: optional T t,
  3: binary s
}

exception InvalidOperation {
  1: i32 what,
  2: string why
}

exception BadRequest {
  1: C c,
  2: B b
}

service Base {
   void ping(),
   TDL merge(1:TDL parent1, 2:TDL parent2) throws (1: InvalidOperation ex1),
   oneway void zip()
}

service Child extends Base {
    i32 get_size(1:A arg) throws (1: InvalidOperation ex1, 2: BadRequest br)
}
