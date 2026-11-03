// Debug oracle emission only: preserve every original register without adding
// a capture network or changing any original declaration/equation.
package checkpoint.reference

import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Paths, StandardOpenOption}
import firrtl.{CircuitState, LowForm, Parser}
import firrtl.annotations.{JsonProtocol, ModuleTarget}
import firrtl.ir._
import firrtl.stage.Forms
import firrtl.stage.transforms.Compiler
import firrtl.transforms.DontTouchAnnotation
import midas.checkpoint.{SemanticCleanEmitter, SemanticStateInventory}
import org.json4s._

object RegisterSnapshotReference {
  def main(args: Array[String]): Unit = {
    require(args.length == 2)
    val input = Paths.get(args(0)); val out = Paths.get(args(1))
    Files.createDirectory(out)
    def read(n: String): String = new String(Files.readAllBytes(input.resolve(n)), UTF_8)
    def write(n: String, s: String): Unit = Files.write(out.resolve(n), s.getBytes(UTF_8), StandardOpenOption.CREATE_NEW)
    val text = read("host.fir")
    val annotations = JsonProtocol.deserialize(read("host-annotations.json"))
    val typed = firrtl.passes.InferTypes.run(firrtl.passes.ResolveKinds.run(
      firrtl.passes.ToWorkingIR.run(Parser.parse(text))))
    val parsed = firrtl.passes.ResolveFlows.run(typed)
    require(parsed.serialize == text, "oracle must preserve the exact original circuit")
    val targets = parsed.modules.collect { case m: Module =>
      val names = scala.collection.mutable.ArrayBuffer.empty[String]
      def visit(s: Statement): Unit = {
        s match {
          case r: DefRegister => names += r.name
          case _: DefMemory => throw new IllegalArgumentException("register oracle does not support memories")
          case _ => ()
        }
        s.foreachStmt(visit)
      }
      visit(m.body)
      names.map(n => ModuleTarget(parsed.main, m.name).ref(n))
    }.flatten
    require(targets.nonEmpty && targets.distinct.size == targets.size)
    val keep = targets.map(DontTouchAnnotation(_))
    val original = CircuitState(parsed, LowForm, annotations)
    val marked = original.copy(annotations = annotations ++ keep)
    require(marked.circuit == original.circuit)
    val emitter = new SemanticCleanEmitter
    val emitted = new Compiler(Seq(firrtl.options.Dependency.fromTransform(emitter)), Forms.LowForm, Set(emitter))
      .execute(marked.copy(annotations = marked.annotations :+ firrtl.EmitCircuitAnnotation(emitter.getClass)))
      .getEmittedCircuit.value
    write("reference.sv", emitted)
    write("original.fir", text)
    write("original-annotations.json", read("host-annotations.json"))
    write("preserved-annotations.json", JsonProtocol.serialize(marked.annotations))
    import SemanticStateInventory.{canonical, sha256}
    write("binding.json", canonical(JObject(List("reference_version" -> JInt(1),
      "scope" -> JString("original_register_oracle_donttouch_only"),
      "original_sha256" -> JString(sha256(text)),
      "original_annotations_sha256" -> JString(sha256(read("host-annotations.json"))),
      "preserved_annotations_sha256" -> JString(sha256(JsonProtocol.serialize(marked.annotations))),
      "reference_verilog_sha256" -> JString(sha256(emitted)),
      "targets" -> JArray(targets.map(_.serialize).sorted.map(JString(_)).toList),
      "original_equations_changed" -> JBool(false), "capture_logic_added" -> JBool(false),
      "physical_fpga_capture" -> JBool(false)))))
    println("REGISTER_REFERENCE_EMITTED " + out)
  }
}
