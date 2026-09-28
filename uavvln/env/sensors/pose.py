class PoseSensor:
    modality = "pose"
    def read(self, state): return state.pose
