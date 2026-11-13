"""Real graphql-core parsing/validation/execution; application resolvers own auth."""
def execute(lab, session, payload):
    try:
        from graphql import build_schema, graphql_sync, GraphQLError
    except ImportError as exc:
        raise RuntimeError('GraphQL requires graphql-core==3.3.0 in .deps; see requirements-http.txt. No automatic install.') from exc
    if not hasattr(lab,'graphql_schema'):
        schema=build_schema('''
          type Item { id: Int!, owner: String!, title: String!, secret: String }
          type Query { item(id: Int!): Item, greeting: String! }
          type Mutation { rename(id: Int!, title: String!): Item }
        ''')
        def user(info):
            if not info.context:
                raise GraphQLError('authentication required',extensions={'code':'UNAUTHENTICATED'})
            return info.context['user']
        def item(_,info,id):
            user(info)
            return lab.items.get(id)
        def secret(row,info):
            if row['owner']!=user(info):
                raise GraphQLError('owner required',extensions={'code':'FORBIDDEN'})
            return 'A-only' if row['owner']=='ayse' else 'B-only'
        def rename(_,info,id,title):
            who=user(info)
            row=lab.items.get(id)
            if row is None: return None
            if row['owner']!=who:
                raise GraphQLError('owner required',extensions={'code':'FORBIDDEN'})
            if not 1<=len(title.strip())<=80:
                raise GraphQLError('title length 1..80',extensions={'code':'BAD_USER_INPUT'})
            row['title']=title.strip(); lab.revision+=1
            return row
        schema.get_type('Query').fields['item'].resolve=item
        schema.get_type('Query').fields['greeting'].resolve=lambda _,info:'hello '+user(info)
        schema.get_type('Item').fields['secret'].resolve=secret
        schema.get_type('Mutation').fields['rename'].resolve=rename
        lab.graphql_schema=schema
    result=graphql_sync(lab.graphql_schema,payload['query'],context_value=session,
                        variable_values=payload.get('variables'),operation_name=payload.get('operationName'))
    return result.formatted
