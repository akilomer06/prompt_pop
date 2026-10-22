import ts from 'typescript'
import fs from 'node:fs'
const config = ts.readConfigFile('tsconfig.json', ts.sys.readFile)
const parsed = ts.parseJsonConfigFileContent(config.config, ts.sys, process.cwd())
const host = {
  getScriptFileNames: () => parsed.fileNames,
  getScriptVersion: () => '0',
  getScriptSnapshot: path => fs.existsSync(path) ? ts.ScriptSnapshot.fromString(fs.readFileSync(path,'utf8')) : undefined,
  getCurrentDirectory: () => process.cwd(),
  getCompilationSettings: () => parsed.options,
  getDefaultLibFileName: options => ts.getDefaultLibFilePath(options),
  fileExists: ts.sys.fileExists, readFile: ts.sys.readFile, readDirectory: ts.sys.readDirectory,
}
const service = ts.createLanguageService(host)
for (const file of parsed.fileNames) {
  for (const group of service.organizeImports({type:'file',fileName:file}, {}, {})) {
    let source = fs.readFileSync(group.fileName,'utf8')
    for (const change of [...group.textChanges].sort((a,b)=>b.span.start-a.span.start)) {
      source=source.slice(0,change.span.start)+change.newText+source.slice(change.span.start+change.span.length)
    }
    fs.writeFileSync(group.fileName,source)
  }
}
