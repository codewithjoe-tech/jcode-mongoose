# jcode-mongoose

Mongoose model definition and populate edges for [jcode](https://github.com/codewithjoes-tech/jcode).

## What it does

Detects Mongoose ORM patterns and emits typed edges — so blast radius queries show every query affected when you rename a model or change a populated field.

| Pattern | Edge emitted |
|---------|-------------|
| `mongoose.model('User', schema)` | `model_define`: module → model node |
| `.populate('posts')` | `populate`: caller → populated field/model |

## Install

```bash
jcode add mongoose
```

## How it works

Once installed, jcode auto-detects this plugin on any repo that has `mongoose` in its `package.json`. No configuration needed.

```js
// jcode sees this:
const User = mongoose.model('User', userSchema)
const Post = mongoose.model('Post', postSchema)

const posts = await Post.find().populate('author')

// and emits:
// module --[model_define]--> User
// module --[model_define]--> Post
// fn     --[populate]------> author
```

The `model()` check requires the receiver to be `mongoose`, `db`, `connection`, or `conn` to avoid false positives from unrelated `.model()` calls.

## Part of the jcode ecosystem

- [jcode](https://github.com/codewithjoes-tech/jcode) — core CLI and MCP server
- [jcode-registry](https://github.com/codewithjoes-tech/jcode-registry) — plugin registry

---

Made by [Joel Thomas](https://codewithjoe.in)
